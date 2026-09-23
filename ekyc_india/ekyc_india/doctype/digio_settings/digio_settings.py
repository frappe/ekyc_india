# Copyright (c) 2025, hello@frappe.io and contributors
# For license information, please see license.txt

import base64
import hashlib
import hmac
import json

import frappe
from frappe import _
from frappe.integrations.utils import make_request
from frappe.model.document import Document
from frappe.utils import now_datetime
from frappe.utils.password import get_decrypted_password

from ekyc_india.kfs import is_kfs_valid


class DigioSettings(Document):
	pass


# Outbound — eSign


def make_esignature_request(doc):
	check_kfs_before_esign(doc)

	general_settings = get_general_settings()
	signers = [
		{
			"identifier": signer,
			"name": get_customer_name(signer),
			"sign_type": "aadhaar",
			"reason": "Please sign the document",
		}
		for signer in get_signers(doc)
	]

	body = frappe._dict(
		signers=signers,
		expire_in_days=general_settings.get("expire_in_days"),
		notify_signers=bool(general_settings.get("notify_customer")),
		send_sign_link=bool(general_settings.get("send_sign_link")),
		generate_access_token=bool(general_settings.get("generate_access_token")),
		file_name=doc.name,
		file_data=get_file_data_in_base64(doc.doctype, doc.name, print_format=get_esign_print_format(doc)),
	)

	api_client_id, api_client_secret, base_url = get_api_credentials_and_url()
	response = make_request(
		method="POST",
		url=f"{base_url}/v2/client/document/uploadpdf",
		headers=get_auth_headers(api_client_id, api_client_secret),
		json=body,
	)

	save_request_log(
		response,
		linked_doctype=doc.doctype,
		linked_docname=doc.name,
		request_type="eSign",
		kfs_version=doc.get("kfs_version"),
	)


def get_esign_print_format(doc):
	if (
		doc.doctype == "Loan Application"
		and "lending" in frappe.get_installed_apps()
		and is_kfs_valid(doc)
		and frappe.db.get_single_value("Loan Origination Settings", "enforce_kfs_before_esign")
	):
		return "Key Facts Statement"
	return None


def check_kfs_before_esign(doc):
	if doc.doctype != "Loan Application" or "lending" not in frappe.get_installed_apps():
		return

	if not frappe.db.get_single_value("Loan Origination Settings", "enforce_kfs_before_esign"):
		return

	if not is_kfs_valid(doc):
		frappe.throw(_("Please generate the Key Facts Statement (KFS) before requesting eSignature."))


# Outbound — eKYC


def make_ekyc_request(doc):
	general_settings = get_general_settings()
	api_client_id, api_client_secret, base_url = get_api_credentials_and_url()

	for signer in get_signers(doc):
		body = frappe._dict(
			customer_identifier=signer,
			notify_customer=True,
			customer_name=get_customer_name(signer),
			template_name="DIGILOCKER_AADHAAR_PAN",
			expire_in_days=general_settings.get("expire_in_days"),
			generate_access_token=general_settings.get("generate_access_token"),
			reference_id=doc.name,
			transaction_id=frappe.generate_hash(length=12),
			generate_deeplink_info=False,
		)

		response = make_request(
			method="POST",
			url=f"{base_url}/client/kyc/v2/request/with_template",
			headers=get_auth_headers(api_client_id, api_client_secret),
			json=body,
		)

		save_request_log(response, linked_doctype=doc.doctype, linked_docname=doc.name, request_type="eKYC")


# Webhook endpoint


# nosemgrep: guest-whitelisted-method
@frappe.whitelist(allow_guest=True)
def handle_webhook():
	try:
		verify_webhook_credentials()
		payload = parse_webhook_payload()
		dispatch_webhook_event(payload)
		return {"status": "ok"}
	except frappe.AuthenticationError:
		frappe.local.response["http_status_code"] = 401
		return {"status": "unauthorized"}
	except Exception:
		frappe.log_error(title="Digio Webhook Error", message=frappe.get_traceback())
		frappe.local.response["http_status_code"] = 500
		return {"status": "error"}


def parse_webhook_payload():
	raw = frappe.request.data
	if not raw:
		frappe.throw(_("Empty webhook body"))
	try:
		return json.loads(raw)
	except json.JSONDecodeError:
		frappe.throw(_("Invalid JSON payload"))


def verify_webhook_credentials():
	expected_secret = get_decrypted_password(
		"Digio Settings", "Digio Settings", fieldname="webhook_secret", raise_exception=False
	)
	if not expected_secret:
		# Fail-secure: refuse all webhooks until a secret is configured.
		frappe.throw(_("Digio webhook secret is not configured"), frappe.AuthenticationError)

	provided_checksum = frappe.request.headers.get("X-Digio-Checksum", "")
	computed_checksum = hmac.new(expected_secret.encode(), frappe.request.data, hashlib.sha256).hexdigest()

	if not provided_checksum or not hmac.compare_digest(provided_checksum, computed_checksum):
		frappe.throw(_("Digio webhook authentication failed"), frappe.AuthenticationError)


# Webhook dispatcher


def dispatch_webhook_event(payload):
	event = (payload.get("event") or "").lower().strip()

	status_labels = {
		"kyc.request.approved": "KYC Approved",
		"kyc.request.rejected": "KYC Rejected",
		"kyc.request.expired": "KYC Expired",
		"kyc.request.terminated": "KYC Terminated",
		"kyc.request.created": "KYC Requested",
		"kyc.request.completed": "KYC Completed",
		"kyc.request.review.ready": "KYC Review Ready",
		"doc.signed": "Signed",
		"doc.sign.rejected": "Sign Rejected",
		"doc.sign.failed": "Sign Failed",
		"esign.v3.sign.failed": "eSign Failed",
		"esign.v3.sign.pending": "eSign Pending",
	}

	if event in status_labels:
		log_webhook_status(payload, event, status_labels[event])
	else:
		frappe.log_error(title="Digio Unhandled Event", message=json.dumps(payload, indent=2))


# Webhook handler — updates Digio Request Log, and for a signed eSign
# request, records KFS acknowledgement on the linked Loan Application.


def log_webhook_status(payload, event, status):
	if event.startswith("kyc."):
		kyc_request = get_kyc_request_data(payload)
		digio_id = kyc_request.get("id") or payload.get("id")
	else:
		document = get_document_data(payload)
		digio_id = document.get("id") or payload.get("id")

	log = update_request_log(digio_id=digio_id, status=status, raw_payload=payload)

	if event == "doc.signed":
		acknowledge_kfs_on_signed(log)


def acknowledge_kfs_on_signed(log):
	if not (
		log.linked_doctype == "Loan Application"
		and log.linked_docname
		and "lending" in frappe.get_installed_apps()
	):
		return

	if not log.get("kfs_version"):
		return

	current_kfs_version = frappe.db.get_value("Loan Application", log.linked_docname, "kfs_version")
	if current_kfs_version and current_kfs_version == log.kfs_version:
		frappe.db.set_value("Loan Application", log.linked_docname, "borrower_acknowledged", 1)


# Payload extractors


def get_kyc_request_data(payload):
	data = payload.get("payload", {})
	return data.get("kyc_request") or data.get("KYC_REQUEST") or {}


def get_document_data(payload):
	data = payload.get("payload", {})
	return data.get("document") or data.get("DOCUMENT") or {}


# Request log helpers


def save_request_log(response, linked_doctype=None, linked_docname=None, request_type=None, kfs_version=None):
	doc = frappe.new_doc("Digio Request Log")
	doc.digio_id = response.get("id")
	doc.response_json = json.dumps(response, indent=1)
	doc.linked_doctype = linked_doctype
	doc.linked_docname = linked_docname
	doc.request_type = request_type
	doc.kfs_version = kfs_version
	doc.status = "Pending"
	doc.save(ignore_permissions=True)


def update_request_log(digio_id, status, raw_payload):
	existing = frappe.db.get_value("Digio Request Log", {"digio_id": digio_id}, "name")

	if existing:
		log = frappe.get_doc("Digio Request Log", existing)
	else:
		log = frappe.new_doc("Digio Request Log")
		log.digio_id = digio_id

	log.status = status
	log.webhook_received_at = now_datetime()
	log.webhook_payload = json.dumps(raw_payload, indent=2)
	log.save(ignore_permissions=True)

	return log


# Shared utilities


def get_general_settings():
	doc = frappe.get_doc("Digio Settings", "Digio Settings")
	return {
		"expire_in_days": doc.request_expiry_in_days,
		"notify_customer": doc.notify_customers,
		"generate_access_token": doc.generate_access_token,
		"send_sign_link": doc.send_sign_link,
	}


def get_api_credentials_and_url():
	digio_settings = frappe.get_doc("Digio Settings", "Digio Settings")

	if digio_settings.enable_production:
		api_client_id = get_decrypted_password(
			"Digio Settings", "Digio Settings", fieldname="api_client_id", raise_exception=False
		)
		api_client_secret = get_decrypted_password(
			"Digio Settings", "Digio Settings", fieldname="api_secret", raise_exception=False
		)
		url = frappe.get_single_value("Digio Settings", "production_url")
	else:
		if not digio_settings.enable_sandbox:
			frappe.throw(_("Please enable Sandbox or Production mode in Digio Settings"))
		api_client_id = get_decrypted_password(
			"Digio Settings", "Digio Settings", fieldname="sandbox_api_client_id", raise_exception=False
		)
		api_client_secret = get_decrypted_password(
			"Digio Settings", "Digio Settings", fieldname="sandbox_api_secret", raise_exception=False
		)
		url = frappe.get_single_value("Digio Settings", "sandbox_url")

	return api_client_id, api_client_secret, url


def get_file_data_in_base64(doctype, docname, print_format=None):
	return base64.b64encode(
		frappe.get_print(
			doctype, docname, print_format=print_format, as_pdf=True, pdf_generator="wkhtmltopdf"
		)
	).decode()


def get_signers(doc):
	from frappe.email.doctype.notification.notification import _parse_receiver_by_document_field

	signers = []
	receiver_fields = frappe.db.get_all(
		"e-Signature Document",
		filters={"document_type": doc.doctype},
		fields=["request_recipient_by_document_field"],
	)

	for receiver in receiver_fields:
		data_field, child_field = _parse_receiver_by_document_field(
			receiver.request_recipient_by_document_field
		)

		if child_field:
			for d in doc.get(child_field):
				signers.append(d.get(data_field))
		else:
			email_ids = doc.get(data_field).replace(",", "\n")
			signers += email_ids.split("\n")

	return signers


def get_customer_name(email_id):
	return frappe.db.get_value("Customer", {"email_id": email_id}, "customer_name") or ""


def get_auth_headers(api_client_id, api_client_secret):
	return {
		"Content-Type": "application/json",
		"Accept": "application/json",
		"Authorization": "Basic "
		+ base64.b64encode(f"{api_client_id}:{api_client_secret}".encode()).decode(),
	}
