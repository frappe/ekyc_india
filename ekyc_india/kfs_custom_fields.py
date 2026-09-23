# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

from ekyc_india.lending_utils import if_lending_app_installed

KFS_CUSTOM_FIELDS = {
	"Loan Origination Settings": [
		{
			"fieldname": "kfs_settings_section",
			"fieldtype": "Section Break",
			"label": "Key Facts Statement (KFS)",
			"insert_after": "employee_loans",
		},
		{
			"fieldname": "enforce_kfs_before_esign",
			"fieldtype": "Check",
			"label": "Enforce KFS before eSignature",
			"default": "1",
			"description": "As per RBI norms, block the eSignature request until the Key Facts Statement is generated and acknowledged by the borrower.",
			"insert_after": "kfs_settings_section",
		},
	],
	"Loan Application": [
		{
			"fieldname": "kfs_tab",
			"fieldtype": "Tab Break",
			"label": "Key Facts Statement",
			"insert_after": "documents",
		},
		{
			"fieldname": "kfs_section",
			"fieldtype": "Section Break",
			"label": "Key Facts (Annex A - Part 1)",
			"insert_after": "kfs_tab",
		},
		{
			"fieldname": "unique_proposal_number",
			"fieldtype": "Data",
			"label": "Loan Proposal / Account No.",
			"read_only": 1,
			"no_copy": 1,
			"insert_after": "kfs_section",
		},
		{
			"fieldname": "loan_type",
			"fieldtype": "Data",
			"label": "Type of Loan",
			"read_only": 1,
			"insert_after": "unique_proposal_number",
		},
		{
			"fieldname": "column_break_kfs_a",
			"fieldtype": "Column Break",
			"insert_after": "loan_type",
		},
		{
			"fieldname": "kfs_valid_till",
			"fieldtype": "Date",
			"label": "KFS Valid Till",
			"read_only": 1,
			"no_copy": 1,
			"description": "Borrower has at least 3 working days to accept the KFS.",
			"insert_after": "column_break_kfs_a",
		},
		{
			"fieldname": "kfs_version",
			"fieldtype": "Data",
			"label": "KFS Version",
			"hidden": 1,
			"read_only": 1,
			"no_copy": 1,
			"insert_after": "kfs_valid_till",
		},
		{
			"fieldname": "kfs_schedule_section",
			"fieldtype": "Section Break",
			"label": "Repayment Schedule (Annex C)",
			"collapsible": 1,
			"insert_after": "kfs_version",
		},
		{
			"fieldname": "kfs_schedule",
			"fieldtype": "Table",
			"label": "Repayment Schedule",
			"options": "Loan Application KFS Schedule",
			"read_only": 1,
			"no_copy": 1,
			"insert_after": "kfs_schedule_section",
		},
		{
			"fieldname": "qualitative_info_section",
			"fieldtype": "Section Break",
			"label": "Other Qualitative Information (Annex A - Part 2)",
			"insert_after": "kfs_schedule",
		},
		{
			"fieldname": "recovery_agent_clause",
			"fieldtype": "Small Text",
			"label": "Recovery Agents Clause",
			"insert_after": "qualitative_info_section",
		},
		{
			"fieldname": "grievance_redressal_clause",
			"fieldtype": "Small Text",
			"label": "Grievance Redressal Clause",
			"insert_after": "recovery_agent_clause",
		},
		{
			"fieldname": "column_break_kfs_c",
			"fieldtype": "Column Break",
			"insert_after": "grievance_redressal_clause",
		},
		{
			"fieldname": "nodal_officer_phone",
			"fieldtype": "Data",
			"label": "Nodal Grievance Officer Phone",
			"insert_after": "column_break_kfs_c",
		},
		{
			"fieldname": "nodal_officer_email",
			"fieldtype": "Data",
			"label": "Nodal Grievance Officer Email",
			"options": "Email",
			"insert_after": "nodal_officer_phone",
		},
		{
			"fieldname": "kfs_acknowledgement_section",
			"fieldtype": "Section Break",
			"label": "Borrower Acknowledgement",
			"insert_after": "nodal_officer_email",
		},
		{
			"fieldname": "borrower_acknowledged",
			"fieldtype": "Check",
			"label": "Borrower Acknowledged Understanding",
			"default": "0",
			"read_only": 1,
			"no_copy": 1,
			"description": "Borrower has been explained and has acknowledged understanding of the Key Facts Statement.",
			"insert_after": "kfs_acknowledgement_section",
		},
		{
			"fieldname": "acknowledge_kfs_button",
			"fieldtype": "Button",
			"label": "Record Borrower Acknowledgement",
			"description": "Use only after the borrower has confirmed, in their own words, that the KFS was explained and understood.",
			"depends_on": "eval: doc.kfs_valid_till && doc.borrower_acknowledged != 1",
			"insert_after": "borrower_acknowledged",
		},
	],
}


KFS_CUSTOM_FIELD_NAMES_BY_DOCTYPE = {
	doctype: [field["fieldname"] for field in fields] for doctype, fields in KFS_CUSTOM_FIELDS.items()
}

KFS_OBSOLETE_FIELD_NAMES = [
	"interest_rate_type",
	"floating_rate_section",
	"interest_rate_benchmark",
	"spread_over_benchmark",
	"column_break_kfs_b",
	"reset_periodicity",
	"kfs_charges_section",
	"kfs_charges",
	"net_disbursed_amount",
	"annual_percentage_rate",
]


@if_lending_app_installed
def remove_obsolete_kfs_fields():
	for fieldname in KFS_OBSOLETE_FIELD_NAMES:
		name = frappe.db.get_value("Custom Field", {"dt": "Loan Application", "fieldname": fieldname})
		if name:
			frappe.delete_doc("Custom Field", name, ignore_permissions=True, force=True)


@if_lending_app_installed
def create_kfs_custom_fields():
	create_custom_fields(KFS_CUSTOM_FIELDS, ignore_validate=True)


@if_lending_app_installed
def remove_kfs_custom_fields():
	for doctype, fieldnames in KFS_CUSTOM_FIELD_NAMES_BY_DOCTYPE.items():
		for fieldname in fieldnames:
			name = frappe.db.get_value("Custom Field", {"dt": doctype, "fieldname": fieldname})
			if name:
				frappe.delete_doc("Custom Field", name, ignore_permissions=True, force=True)
