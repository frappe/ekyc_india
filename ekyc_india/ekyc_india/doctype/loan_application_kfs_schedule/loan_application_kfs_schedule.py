# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document


class LoanApplicationKFSSchedule(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		instalment_amount: DF.Currency
		instalment_no: DF.Int
		interest_amount: DF.Currency
		outstanding_principal: DF.Currency
		parent: DF.Data
		parentfield: DF.Data
		parenttype: DF.Data
		payment_date: DF.Date | None
		principal_amount: DF.Currency
	# end: auto-generated types

	pass
