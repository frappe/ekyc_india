# Copyright (c) 2026, hello@frappe.io and contributors
# For license information, please see license.txt

"""Surepass, who resell the Indian credit bureaux behind one API."""

import re

import frappe
from frappe import _
from frappe.utils import cint
from lending.loan_integrations.base import IntegrationError
from lending.loan_integrations.bureau import BureauAdapter

SETTINGS = "Surepass Settings"

# Surepass answer HTTP 200 and report the outcome in the body: raise_for_status sees nothing.
SUCCESS_CODE = 200

# A signed link, and an aadhaar number that is not ours to keep. Neither belongs in a report.
DROPPED_FROM_PAYLOAD = ("credit_report_link", "credit_report_base64", "aadhaar_number")

# CIBIL answer below the floor to say why they could not score: -1 no history, 1 to 5 too
# little. Read as a score, "no credit history" becomes "the worst borrower possible".
LOWEST_REAL_SCORE = 300


class SurepassBureauAdapter(BureauAdapter):
	settings_doctype = SETTINGS

	endpoint: str = ""

	def auth_headers(self) -> dict:
		# Not Basic auth: Surepass issue one bearer token, carried in the pair's second half.
		_, token = self.creds()

		if not token:
			frappe.throw(
				_("Set the {0} API Secret in {1} to the token from the Surepass console.").format(
					self.environment().title(), SETTINGS
				)
			)

		return {
			"Content-Type": "application/json",
			"Accept": "application/json",
			"Authorization": f"Bearer {token}",
		}

	def pull(self, context: dict) -> dict:
		return self.request("POST", self.endpoint, json=self.request_body(context))

	def request_body(self, context: dict) -> dict:
		return {
			"mobile": indian_mobile(context.get("mobile")),
			"consent": "Y",
		}

	def parse(self, response: dict) -> dict:
		if not response.get("success") or cint(response.get("status_code")) != SUCCESS_CODE:
			raise IntegrationError(
				_("{0} refused the request: {1}").format(
					self.provider.name, response.get("message") or _("no reason given")
				)
			)

		data = response.get("data") or {}
		score = cint(data.get("credit_score"))

		return {
			"external_id": data.get("client_id"),
			"score": score if score >= LOWEST_REAL_SCORE else 0,
			"obligations_known": False,
			"total_emi": 0,
			"report_url": data.get("credit_report_link"),
			"payload": {k: v for k, v in data.items() if k not in DROPPED_FROM_PAYLOAD},
		}


class SurepassCibilAdapter(SurepassBureauAdapter):
	key = "Surepass CIBIL"
	bureau = "CIBIL"
	endpoint = "/credit-report-cibil/fetch-report-pdf"

	def request_body(self, context: dict) -> dict:
		return {
			**super().request_body(context),
			"pan": context.get("pan"),
			"name": context.get("name"),
			"gender": (context.get("gender") or "").lower(),
		}


class SurepassExperianAdapter(SurepassBureauAdapter):
	key = "Surepass Experian"
	bureau = "Experian"
	endpoint = "/credit-report-experian/fetch-report-pdf"

	def request_body(self, context: dict) -> dict:
		return {**super().request_body(context), "pan": context.get("pan"), "name": context.get("name")}


class SurepassCrifAdapter(SurepassBureauAdapter):
	key = "Surepass CRIF"
	bureau = "CRIF"
	endpoint = "/credit-report-crif/fetch-report-pdf"

	raw_report = False

	def request_body(self, context: dict) -> dict:
		first_name, last_name = split_name(context.get("name"))

		return {
			**super().request_body(context),
			"pan": context.get("pan"),
			"first_name": first_name,
			"last_name": last_name,
			"raw": self.raw_report,
		}


class SurepassEquifaxAdapter(SurepassBureauAdapter):
	key = "Surepass Equifax"
	# The path says only v2 and the response names no bureau. Equifax is Surepass's word.
	bureau = "Equifax"
	endpoint = "/credit-report-v2/fetch-pdf-report"

	def request_body(self, context: dict) -> dict:
		return {
			**super().request_body(context),
			"name": context.get("name"),
			"gender": (context.get("gender") or "").lower(),
			"id_number": context.get("pan"),
			"id_type": "pan",
		}


def split_name(full_name: str | None) -> tuple[str, str]:
	parts = (full_name or "").split()

	if not parts:
		return "", ""

	return parts[0], " ".join(parts[1:])


def indian_mobile(value: str | None) -> str:
	digits = re.sub(r"\D", "", value or "")

	if len(digits) == 12 and digits.startswith("91"):
		return digits[2:]

	if len(digits) == 11 and digits.startswith("0"):
		return digits[1:]

	return digits
