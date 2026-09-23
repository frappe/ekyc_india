# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe

from ekyc_india.kfs_custom_fields import (
	KFS_CUSTOM_FIELDS,
	create_kfs_custom_fields,
	remove_obsolete_kfs_fields,
)


def execute():
	create_kfs_custom_fields()
	remove_obsolete_kfs_fields()

	for doctype, fields in KFS_CUSTOM_FIELDS.items():
		for field in fields:
			name = f"{doctype}-{field['fieldname']}"
			if frappe.db.exists("Custom Field", name):
				frappe.db.set_value(
					"Custom Field",
					name,
					{
						"label": field.get("label"),
						"description": field.get("description", ""),
						"depends_on": field.get("depends_on", ""),
					},
				)
