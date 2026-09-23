# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from ekyc_india.kfs_custom_fields import create_kfs_custom_fields


def after_install():
	create_kfs_custom_fields()


def after_app_install(app_name):
	if app_name == "lending":
		create_kfs_custom_fields()
