# Copyright (c) 2026, hello@frappe.io and contributors
# For license information, please see license.txt

import json

import frappe
from frappe import _
from frappe.model.document import Document


class SurepassSettings(Document):
	"""Imports nothing from lending: this form has to stand up on a site without it."""

	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		api_client_id: DF.Password | None
		api_secret: DF.Password | None
		enable_production: DF.Check
		enable_sandbox: DF.Check
		extra_config: DF.SmallText | None
		production_url: DF.Data | None
		sandbox_api_client_id: DF.Password | None
		sandbox_api_secret: DF.Password | None
		sandbox_url: DF.Data | None
		timeout: DF.Int
	# end: auto-generated types

	def validate(self):
		self.normalise_urls()
		self.validate_extra_config()

	def normalise_urls(self):
		# The adapter joins a path straight on, and a doubled slash is a 404 from Surepass.
		for fieldname in ("production_url", "sandbox_url"):
			if url := self.get(fieldname):
				self.set(fieldname, url.strip().rstrip("/"))

	def validate_extra_config(self):
		if not self.extra_config:
			return

		try:
			config = json.loads(self.extra_config)
		except json.JSONDecodeError as e:
			frappe.throw(_("Extra Config is not valid JSON: {0}").format(str(e)))

		if not isinstance(config, dict):
			frappe.throw(_("Extra Config has to be a JSON object, such as {0}.").format('{"key": "value"}'))
