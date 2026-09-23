# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe

from ekyc_india.kfs_custom_fields import remove_kfs_custom_fields


def before_uninstall():
	remove_kfs_custom_fields()
	remove_kfs_print_format()
	remove_kfs_child_doctypes()


def remove_kfs_print_format():
	if frappe.db.exists("Print Format", "Key Facts Statement"):
		frappe.delete_doc("Print Format", "Key Facts Statement", ignore_permissions=True, force=True)


def remove_kfs_child_doctypes():
	if frappe.db.exists("DocType", "Loan Application KFS Schedule"):
		frappe.delete_doc("DocType", "Loan Application KFS Schedule", ignore_permissions=True, force=True)
