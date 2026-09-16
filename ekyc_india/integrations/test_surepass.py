# Copyright (c) 2026, hello@frappe.io and contributors
# See license.txt

import unittest

import frappe
from frappe.tests import IntegrationTestCase

# The adapters subclass lending's BureauAdapter; this app installs without lending.
HAS_LENDING = "lending" in frappe.get_installed_apps()

if HAS_LENDING:
	from lending.loan_integrations.base import IntegrationError

	from ekyc_india.integrations.surepass import (
		SurepassCibilAdapter,
		SurepassCrifAdapter,
		SurepassEquifaxAdapter,
		SurepassExperianAdapter,
	)

TEST_PAN = "EKRPR1234F"
TOKEN = "a-test-token"
SANDBOX_URL = "https://sandboxapp.surepass.app/sandbox/api/v1"

SANDBOX_RESPONSE = {
	"data": {
		"client_id": "credit_report_cibil_pdf_xfOSfdDRgierjgNdZelb",
		"name": "VISHAL RATHORE",
		"mobile": "9988776655",
		"pan": TEST_PAN,
		"gender": "male",
		"user_email": None,
		"credit_score": "750",
		"credit_report": None,
		"credit_report_link": (
			"https://aadhaar-kyc-docs.s3.amazonaws.com/user123/credit_report_cibil/report.pdf"
			"?X-Amz-Credential=AKIAY5K3QRM5KVPBYKKE%2F20260806%2Fap-south-1%2Fs3%2Faws4_request"
			"&X-Amz-Expires=600&X-Amz-Signature=c5168167bdab60bf30e2b27ac148585a4b474633"
		),
		"credit_report_base64": None,
	},
	"status_code": 200,
	"success": True,
	"message": "Success",
	"message_code": "success",
}


CRIF_RESPONSE = {
	"data": {
		"client_id": "credit_report_crif_pdf_QuSYiwhmGFqfwuegPVqj",
		"first_name": "Rahul",
		"last_name": "Sharma",
		"mobile": "9876543210",
		"pan": "AXYPR5678L",
		"aadhaar_number": None,
		"credit_score": "734",
		"credit_report": {},
		"credit_report_link": (
			"https://temp-surepass-bucket.s3.amazonaws.com/x/credit_report_crif/report.pdf"
			"?X-Amz-Credential=AKIAY5K3QRM5JDBTSGYP%2F20250724%2Fap-south-1%2Fs3%2Faws4_request"
			"&X-Amz-Expires=600&X-Amz-Signature=3ffacd2813c59d19c77789b009837b64e182136a5"
		),
	},
	"status_code": 200,
	"success": True,
	"message": "Success",
	"message_code": "success",
}


EXPERIAN_RESPONSE = {
	"data": {
		"client_id": "credit_report_experian_pdf_yzWulawpzCczmLyKazqJ",
		"name": "MAHENDRA SINGH RAJPUT",
		"mobile": "8890812345",
		"pan": "FPVPR1234Q",
		"credit_score": "761",
		"credit_report": {},
		"credit_report_link": (
			"https://aadhaar-kyc-docs.s3.amazonaws.com/x/credit_report_experian/report.pdf"
			"?X-Amz-Credential=AKIAY5K3QRM5FYWPQJEB%2F20241029%2Fap-south-1%2Fs3%2Faws"
		),
	},
	"status_code": 200,
	"success": True,
	"message": "Success",
	"message_code": "success",
}


EQUIFAX_RESPONSE = {
	"data": {
		"client_id": "credit_report_v2_pdf_ywWaXdhazoIEjbpPuvqc",
		"id_number": "********5514",
		"id_type": "aadhaar",
		"mobile": "8079012345",
		"name": "Vishal Rathore",
		"credit_score": "799",
		"credit_report": {},
		"credit_report_link": "https://aadhaar-kyc-docs.s3.amazonaws.com/x/credit_report_v2/r.pdf?sig=568a2c",
	},
	"status_code": 200,
	"success": True,
	"message": "Success",
	"message_code": "success",
}


@unittest.skipUnless(HAS_LENDING, "the Surepass bureau adapters need the lending app")
class TestSurepassBureau(IntegrationTestCase):
	def setUp(self):
		settings = frappe.get_single("Surepass Settings")
		settings.update(
			{
				"enable_production": 0,
				"enable_sandbox": 1,
				"sandbox_url": SANDBOX_URL,
				"sandbox_api_secret": TOKEN,
			}
		)
		settings.save(ignore_permissions=True)

		self.adapter = SurepassCibilAdapter(frappe._dict(name="Surepass CIBIL"))

	def test_it_reads_the_score_out_of_the_envelope(self):
		parsed = self.adapter.parse(SANDBOX_RESPONSE)

		self.assertEqual(parsed["score"], 750)
		self.assertEqual(parsed["external_id"], "credit_report_cibil_pdf_xfOSfdDRgierjgNdZelb")

	def test_it_does_not_claim_to_know_the_obligations(self):
		self.assertFalse(self.adapter.parse(SANDBOX_RESPONSE)["obligations_known"])

	def test_it_keeps_the_signed_link_out_of_the_stored_payload(self):
		parsed = self.adapter.parse(SANDBOX_RESPONSE)

		self.assertNotIn("credit_report_link", parsed["payload"])
		self.assertNotIn("AKIAY5K3QRM5KVPBYKKE", frappe.as_json(parsed["payload"]))
		self.assertIn("X-Amz-Signature", parsed["report_url"])

	def test_a_score_below_the_floor_is_not_a_score(self):
		response = {**SANDBOX_RESPONSE, "data": {**SANDBOX_RESPONSE["data"], "credit_score": "-1"}}

		self.assertEqual(self.adapter.parse(response)["score"], 0)

	def test_a_failure_reported_in_the_body_is_a_failure(self):
		response = {**SANDBOX_RESPONSE, "success": False, "message": "PAN not found"}

		with self.assertRaises(IntegrationError):
			self.adapter.parse(response)

	def test_the_request_body_carries_what_the_bureau_asks_for(self):
		body = self.adapter.request_body(
			{"name": "Vishal Rathore", "pan": TEST_PAN, "mobile": "9988776655", "gender": "Male"}
		)

		self.assertEqual(body["gender"], "male")
		self.assertEqual(body["pan"], TEST_PAN)

	def test_a_number_is_sent_as_ten_bare_digits(self):
		for typed in ("+91-9988776655", "+91 99887 76655", "09988776655", "9988776655"):
			body = self.adapter.request_body({"mobile": typed})

			self.assertEqual(body["mobile"], "9988776655", f"failed for {typed}")

	def test_it_authenticates_with_a_bearer_token(self):
		self.assertEqual(self.adapter.auth_headers()["Authorization"], f"Bearer {TOKEN}")

	def test_it_reads_its_own_settings_rather_than_the_provider_row(self):
		self.assertEqual(self.adapter.settings.doctype, "Surepass Settings")
		self.assertEqual(self.adapter.get_base_url(), SANDBOX_URL)


@unittest.skipUnless(HAS_LENDING, "the Surepass bureau adapters need the lending app")
class TestSurepassCrif(IntegrationTestCase):
	def setUp(self):
		settings = frappe.get_single("Surepass Settings")
		settings.update(
			{
				"enable_production": 0,
				"enable_sandbox": 1,
				"sandbox_url": SANDBOX_URL,
				"sandbox_api_secret": TOKEN,
			}
		)
		settings.save(ignore_permissions=True)

		self.crif = SurepassCrifAdapter(frappe._dict(name="Surepass CRIF"))

	def test_it_shares_the_envelope_and_the_token_with_cibil(self):
		self.assertEqual(self.crif.parse(CRIF_RESPONSE)["score"], 734)
		self.assertEqual(self.crif.auth_headers()["Authorization"], f"Bearer {TOKEN}")
		self.assertEqual(self.crif.bureau, "CRIF")

	def test_it_asks_in_the_two_halves_crif_want(self):
		body = self.crif.request_body(
			{"name": "Rahul Sharma", "pan": "AXYPR5678L", "mobile": "+91-9876543210"}
		)

		self.assertEqual(body["first_name"], "Rahul")
		self.assertEqual(body["last_name"], "Sharma")
		self.assertEqual(body["mobile"], "9876543210")
		self.assertEqual(body["consent"], "Y")
		self.assertNotIn("gender", body)
		self.assertNotIn("name", body)

	def test_a_name_of_more_than_two_words_keeps_them_all(self):
		body = self.crif.request_body({"name": "Rahul Kumar Sharma"})
		self.assertEqual((body["first_name"], body["last_name"]), ("Rahul", "Kumar Sharma"))

		body = self.crif.request_body({"name": "Rahul"})
		self.assertEqual((body["first_name"], body["last_name"]), ("Rahul", ""))

	def test_an_empty_report_is_not_a_claim_to_know_the_obligations(self):
		self.assertFalse(self.crif.parse(CRIF_RESPONSE)["obligations_known"])

	def test_the_aadhaar_number_is_never_stored(self):
		response = {**CRIF_RESPONSE, "data": {**CRIF_RESPONSE["data"], "aadhaar_number": "123412341234"}}
		parsed = self.crif.parse(response)

		self.assertNotIn("aadhaar_number", parsed["payload"])
		self.assertNotIn("123412341234", frappe.as_json(parsed["payload"]))

	def test_it_keeps_the_signed_link_out_of_the_stored_payload(self):
		parsed = self.crif.parse(CRIF_RESPONSE)

		self.assertNotIn("AKIAY5K3QRM5JDBTSGYP", frappe.as_json(parsed["payload"]))
		self.assertIn("X-Amz-Signature", parsed["report_url"])


@unittest.skipUnless(HAS_LENDING, "the Surepass bureau adapters need the lending app")
class TestSurepassExperian(IntegrationTestCase):
	def setUp(self):
		settings = frappe.get_single("Surepass Settings")
		settings.update(
			{
				"enable_production": 0,
				"enable_sandbox": 1,
				"sandbox_url": SANDBOX_URL,
				"sandbox_api_secret": TOKEN,
			}
		)
		settings.save(ignore_permissions=True)

		self.experian = SurepassExperianAdapter(frappe._dict(name="Surepass Experian"))

	def test_it_reads_the_score_out_of_the_same_envelope(self):
		parsed = self.experian.parse(EXPERIAN_RESPONSE)

		self.assertEqual(parsed["score"], 761)
		self.assertEqual(parsed["external_id"], "credit_report_experian_pdf_yzWulawpzCczmLyKazqJ")
		self.assertEqual(self.experian.bureau, "Experian")

	def test_it_asks_by_whole_name_and_never_for_a_gender(self):
		body = self.experian.request_body(
			{"name": "Mahendra Singh Rajput", "pan": "FPVPR1234Q", "mobile": "8890812345", "gender": "Male"}
		)

		self.assertEqual(body["name"], "Mahendra Singh Rajput")
		self.assertEqual(body["consent"], "Y")
		self.assertNotIn("gender", body)

	def test_an_empty_report_is_not_a_claim_to_know_the_obligations(self):
		self.assertFalse(self.experian.parse(EXPERIAN_RESPONSE)["obligations_known"])

	def test_it_keeps_the_signed_link_out_of_the_stored_payload(self):
		parsed = self.experian.parse(EXPERIAN_RESPONSE)

		self.assertNotIn("AKIAY5K3QRM5FYWPQJEB", frappe.as_json(parsed["payload"]))
		self.assertIn("X-Amz-Credential", parsed["report_url"])


@unittest.skipUnless(HAS_LENDING, "the Surepass bureau adapters need the lending app")
class TestEveryBureauSharesTheMachinery(IntegrationTestCase):
	def setUp(self):
		settings = frappe.get_single("Surepass Settings")
		settings.update({"enable_sandbox": 1, "sandbox_url": SANDBOX_URL, "sandbox_api_secret": TOKEN})
		settings.save(ignore_permissions=True)

	def test_each_bureau_parses_and_authenticates_the_same_way(self):
		cases = [
			(SurepassCibilAdapter, "CIBIL", SANDBOX_RESPONSE, 750),
			(SurepassCrifAdapter, "CRIF", CRIF_RESPONSE, 734),
			(SurepassExperianAdapter, "Experian", EXPERIAN_RESPONSE, 761),
			(SurepassEquifaxAdapter, "Equifax", EQUIFAX_RESPONSE, 799),
		]

		for cls, bureau, response, score in cases:
			adapter = cls(frappe._dict(name=cls.key))
			parsed = adapter.parse(response)

			self.assertEqual(adapter.bureau, bureau)
			self.assertEqual(parsed["score"], score)
			self.assertEqual(adapter.auth_headers()["Authorization"], f"Bearer {TOKEN}")
			self.assertFalse(parsed["obligations_known"])
			self.assertNotIn("credit_report_link", parsed["payload"])
			self.assertEqual(adapter.settings_doctype, "Surepass Settings")

	def test_every_bureau_asks_for_consent_and_a_number_to_match_on(self):
		context = {"name": "Rahul Sharma", "pan": "AXYPR5678L", "mobile": "+91-9876543210"}

		for cls in (
			SurepassCibilAdapter,
			SurepassCrifAdapter,
			SurepassExperianAdapter,
			SurepassEquifaxAdapter,
		):
			body = cls(frappe._dict(name=cls.key)).request_body(context)

			self.assertEqual(body["consent"], "Y", cls.key)
			self.assertEqual(body["mobile"], "9876543210", cls.key)

	def test_every_bureau_sends_the_pan_in_the_field_that_bureau_reads(self):
		context = {"name": "Rahul Sharma", "pan": "AXYPR5678L", "mobile": "9876543210"}

		for cls in (SurepassCibilAdapter, SurepassCrifAdapter, SurepassExperianAdapter):
			self.assertEqual(
				cls(frappe._dict(name=cls.key)).request_body(context)["pan"], "AXYPR5678L", cls.key
			)

		equifax = SurepassEquifaxAdapter(frappe._dict(name="Surepass Equifax")).request_body(context)

		self.assertEqual(equifax["id_number"], "AXYPR5678L")
		self.assertEqual(equifax["id_type"], "pan")
		self.assertNotIn("pan", equifax)


@unittest.skipUnless(HAS_LENDING, "the Surepass bureau adapters need the lending app")
class TestSurepassEquifax(IntegrationTestCase):
	def setUp(self):
		settings = frappe.get_single("Surepass Settings")
		settings.update({"enable_sandbox": 1, "sandbox_url": SANDBOX_URL, "sandbox_api_secret": TOKEN})
		settings.save(ignore_permissions=True)

		self.equifax = SurepassEquifaxAdapter(frappe._dict(name="Surepass Equifax"))

	def test_it_reads_the_score_out_of_the_same_envelope(self):
		parsed = self.equifax.parse(EQUIFAX_RESPONSE)

		self.assertEqual(parsed["score"], 799)
		self.assertEqual(parsed["external_id"], "credit_report_v2_pdf_ywWaXdhazoIEjbpPuvqc")

	def test_it_files_the_report_under_the_bureau_surepass_name(self):
		self.assertEqual(self.equifax.bureau, "Equifax")

	def test_the_identity_it_answers_with_is_not_the_one_it_was_asked_about(self):
		parsed = self.equifax.parse(EQUIFAX_RESPONSE)

		self.assertEqual(parsed["payload"]["id_type"], "aadhaar")
		self.assertNotIn("AXYPR5678L", frappe.as_json(parsed["payload"]))

	def test_an_empty_report_is_not_a_claim_to_know_the_obligations(self):
		self.assertFalse(self.equifax.parse(EQUIFAX_RESPONSE)["obligations_known"])
