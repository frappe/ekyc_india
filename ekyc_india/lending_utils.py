# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import functools

import frappe


def if_lending_app_installed(function):
	@functools.wraps(function)
	def wrapper(*args, **kwargs):
		if "lending" in frappe.get_installed_apps():
			return function(*args, **kwargs)
		return

	return wrapper
