# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import hashlib

import frappe
from frappe import _
from frappe.utils import add_days, flt, getdate

from ekyc_india.lending_utils import if_lending_app_installed


@if_lending_app_installed
def loan_application_before_save(doc, method=None):
	if (
		doc.get("is_term_loan")
		and doc.get("loan_amount")
		and doc.get("rate_of_interest")
		and doc.get("repayment_periods")
	):
		build_kfs(doc)


def build_kfs(doc):
	if not doc.get("is_term_loan"):
		frappe.throw(_("Key Facts Statement can be generated only for term loans."))

	if not (doc.get("loan_amount") and doc.get("rate_of_interest") and doc.get("repayment_periods")):
		frappe.throw(
			_("Loan Amount, Rate of Interest and Repayment Periods are required to generate the KFS.")
		)

	doc.get_repayment_details()

	if not doc.get("unique_proposal_number"):
		doc.unique_proposal_number = doc.name or frappe.generate_hash(length=10).upper()

	if not doc.get("loan_type"):
		doc.loan_type = frappe.db.get_value("Loan Product", doc.loan_product, "product_name")

	schedule = get_proposed_repayment_schedule(doc)
	set_kfs_validity(doc, schedule)
	build_kfs_schedule(doc, schedule)

	new_version = compute_kfs_version(doc)
	if new_version != doc.get("kfs_version"):
		doc.kfs_version = new_version
		doc.borrower_acknowledged = 0


def compute_kfs_version(doc):
	# Hash the rendered KFS print format so the version reflects everything
	# the borrower actually sees, not a hand-picked subset of fields. Fields
	# that are an outcome of a version rather than part of its content are
	# pinned so they don't affect the hash.
	snapshot = frappe.copy_doc(doc, ignore_no_copy=True)
	snapshot.name = "KFS-VERSION-SNAPSHOT"
	snapshot.borrower_acknowledged = 0
	snapshot.kfs_valid_till = "1970-01-01"

	print_format = frappe.get_doc("Print Format", "Key Facts Statement")
	# print_format.html is this app's own hardcoded "Key Facts Statement" format, not user input.
	html = frappe.render_template(print_format.html, {"doc": snapshot})  # nosemgrep: frappe-ssti
	return hashlib.sha256(html.encode()).hexdigest()[:10]


def set_kfs_validity(doc, schedule):
	# RBI: validity is 3 working days, except loans with tenor under 7 days get 1 working day.
	tenor_days = (getdate(schedule[-1].payment_date) - getdate()).days if schedule else 0
	working_days = 1 if tenor_days < 7 else 3
	doc.kfs_valid_till = add_working_days(getdate(), working_days)


def build_kfs_schedule(doc, schedule):
	doc.set("kfs_schedule", [])

	for instalment_no, row in enumerate(schedule, start=1):
		doc.append(
			"kfs_schedule",
			{
				"instalment_no": instalment_no,
				"payment_date": row.payment_date,
				"outstanding_principal": flt(row.balance_loan_amount) + flt(row.principal_amount),
				"principal_amount": row.principal_amount,
				"interest_amount": row.interest_amount,
				"instalment_amount": row.total_payment,
			},
		)


def get_proposed_repayment_schedule(doc):
	repayment_schedule = frappe.new_doc("Loan Repayment Schedule")
	repayment_schedule.loan_product = doc.loan_product
	repayment_schedule.repayment_frequency = "Monthly"
	repayment_schedule.repayment_method = "Repay Over Number of Periods"
	repayment_schedule.repayment_periods = doc.repayment_periods
	repayment_schedule.rate_of_interest = doc.rate_of_interest
	repayment_schedule.posting_date = getdate()
	repayment_schedule.repayment_start_date = getdate()
	repayment_schedule.loan_amount = doc.loan_amount
	repayment_schedule.current_principal_amount = doc.loan_amount
	repayment_schedule.moratorium_tenure = 0
	repayment_schedule.moratorium_type = ""
	repayment_schedule.repayment_schedule_type = frappe.db.get_value(
		"Loan Product", doc.loan_product, "repayment_schedule_type"
	)
	repayment_schedule.validate()

	return repayment_schedule.get("repayment_schedule")


def add_working_days(start_date, working_days):
	current = getdate(start_date)
	added = 0
	while added < working_days:
		current = add_days(current, 1)
		if current.weekday() < 5:
			added += 1
	return current


def is_kfs_valid(doc):
	kfs_valid_till = doc.get("kfs_valid_till")
	return bool(kfs_valid_till) and getdate(kfs_valid_till) >= getdate()


@frappe.whitelist()
@if_lending_app_installed
def acknowledge_kfs(loan_application: str):
	if not isinstance(loan_application, str):
		frappe.throw(_("Loan Application must be a string."), frappe.ValidationError)

	doc = frappe.get_doc("Loan Application", loan_application)
	doc.check_permission("write")

	if not is_kfs_valid(doc):
		frappe.throw(
			_(
				"Generate a valid Key Facts Statement (KFS) before recording acknowledgement. "
				"The current KFS has expired."
			)
		)

	doc.db_set("borrower_acknowledged", 1)
	return doc.name
