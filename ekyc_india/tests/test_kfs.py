# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# See license.txt

import datetime
import unittest

import frappe
from frappe.tests import IntegrationTestCase, UnitTestCase
from frappe.utils import add_days, getdate

from ekyc_india.kfs import acknowledge_kfs, add_working_days, build_kfs, set_kfs_validity

LENDING_INSTALLED = "lending" in frappe.get_installed_apps()


class UnitTestKFSCalculations(UnitTestCase):
	def test_add_working_days_skips_weekend(self):
		friday = datetime.date(2026, 6, 19)
		self.assertEqual(add_working_days(friday, 3), datetime.date(2026, 6, 24))

	def test_add_one_working_day(self):
		friday = datetime.date(2026, 6, 19)
		self.assertEqual(add_working_days(friday, 1), datetime.date(2026, 6, 22))


@unittest.skipUnless(LENDING_INSTALLED, "Lending app is not installed")
class IntegrationTestKFSOnLoanApplication(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		from erpnext.setup.doctype.employee.test_employee import make_employee
		from lending.tests.test_utils import (
			create_loan_accounts,
			create_loan_product,
			set_loan_settings_in_company,
		)

		set_loan_settings_in_company()
		create_loan_accounts()
		create_loan_product(
			"KFS Home Loan",
			"KFS Home Loan",
			500000,
			9.2,
			0,
			1,
			0,
			repayment_schedule_type="Monthly as per repayment start date",
		)
		cls.applicant = make_employee("kfs_kate@loan.com", "_Test Company")

	def make_application(self):
		loan_application = frappe.new_doc("Loan Application")
		loan_application.update(
			{
				"applicant_type": "Employee",
				"applicant": self.applicant,
				"loan_product": "KFS Home Loan",
				"rate_of_interest": 9.2,
				"loan_amount": 250000,
				"repayment_method": "Repay Over Number of Periods",
				"repayment_periods": 18,
				"company": "_Test Company",
				"applicant_email_address": "lending@example.com",
				"applicant_phone_number": "+91-9102837465",
			}
		)
		loan_application.insert()
		return loan_application

	def test_kfs_generation(self):
		doc = self.make_application()
		build_kfs(doc)

		self.assertTrue(doc.unique_proposal_number)
		self.assertTrue(doc.kfs_valid_till)
		self.assertEqual(len(doc.kfs_schedule), doc.repayment_periods)

	def test_kfs_schedule_closes_principal(self):
		doc = self.make_application()
		build_kfs(doc)

		self.assertEqual(doc.kfs_schedule[0].outstanding_principal, doc.loan_amount)

		total_principal = sum(row.principal_amount for row in doc.kfs_schedule)
		self.assertAlmostEqual(total_principal, doc.loan_amount, delta=1)

		last_row = doc.kfs_schedule[-1]
		closing_balance = last_row.outstanding_principal - last_row.principal_amount
		self.assertAlmostEqual(closing_balance, 0, delta=1)

	def test_kfs_validity_is_one_working_day_for_short_tenor(self):
		doc = self.make_application()
		doc.repayment_periods = 1
		schedule = [frappe._dict(payment_date=add_days(getdate(), 5))]
		set_kfs_validity(doc, schedule)
		self.assertEqual(doc.kfs_valid_till, add_working_days(getdate(), 1))

	def test_kfs_validity_is_three_working_days_for_longer_tenor(self):
		doc = self.make_application()
		build_kfs(doc)
		self.assertEqual(doc.kfs_valid_till, add_working_days(getdate(), 3))

	def test_kfs_requires_term_loan(self):
		doc = self.make_application()
		doc.is_term_loan = 0
		self.assertRaises(frappe.ValidationError, build_kfs, doc)

	def test_kfs_auto_generated_on_save(self):
		doc = self.make_application()
		self.assertTrue(doc.kfs_valid_till)
		self.assertEqual(len(doc.kfs_schedule), doc.repayment_periods)

	def test_esign_blocked_until_kfs_generated(self):
		from ekyc_india.ekyc_india.doctype.digio_settings.digio_settings import (
			check_kfs_before_esign,
		)

		doc = self.make_application()
		doc.db_set("kfs_valid_till", None)
		frappe.db.set_single_value("Loan Origination Settings", "enforce_kfs_before_esign", 1)

		self.assertRaises(frappe.ValidationError, check_kfs_before_esign, doc)

		doc.reload()
		check_kfs_before_esign(doc)

		frappe.db.set_single_value("Loan Origination Settings", "enforce_kfs_before_esign", 0)
		doc.db_set("kfs_valid_till", None)
		check_kfs_before_esign(doc)
		frappe.db.set_single_value("Loan Origination Settings", "enforce_kfs_before_esign", 1)

	def test_esign_blocked_when_kfs_expired(self):
		from ekyc_india.ekyc_india.doctype.digio_settings.digio_settings import (
			check_kfs_before_esign,
			get_esign_print_format,
		)

		doc = self.make_application()
		frappe.db.set_single_value("Loan Origination Settings", "enforce_kfs_before_esign", 1)

		doc.db_set("kfs_valid_till", add_days(getdate(), -1))
		self.assertRaises(frappe.ValidationError, check_kfs_before_esign, doc)
		self.assertIsNone(get_esign_print_format(doc))

	def test_esign_print_format_is_kfs_when_enforced(self):
		from ekyc_india.ekyc_india.doctype.digio_settings.digio_settings import get_esign_print_format

		doc = self.make_application()
		frappe.db.set_single_value("Loan Origination Settings", "enforce_kfs_before_esign", 1)

		self.assertEqual(get_esign_print_format(doc), "Key Facts Statement")

		frappe.db.set_single_value("Loan Origination Settings", "enforce_kfs_before_esign", 0)
		self.assertIsNone(get_esign_print_format(doc))
		frappe.db.set_single_value("Loan Origination Settings", "enforce_kfs_before_esign", 1)

	def test_signed_webhook_acknowledges_kfs(self):
		from ekyc_india.ekyc_india.doctype.digio_settings.digio_settings import (
			acknowledge_kfs_on_signed,
		)

		doc = self.make_application()
		self.assertFalse(doc.borrower_acknowledged)

		log = frappe._dict(
			linked_doctype="Loan Application", linked_docname=doc.name, kfs_version=doc.kfs_version
		)
		acknowledge_kfs_on_signed(log)

		self.assertEqual(frappe.db.get_value("Loan Application", doc.name, "borrower_acknowledged"), 1)

	def test_signed_webhook_ignores_stale_kfs_version(self):
		from ekyc_india.ekyc_india.doctype.digio_settings.digio_settings import (
			acknowledge_kfs_on_signed,
		)

		doc = self.make_application()
		stale_version = doc.kfs_version

		# Changing terms same-day must still change kfs_version.
		doc.loan_amount = 300000
		doc.save()
		self.assertNotEqual(doc.kfs_version, stale_version)

		log = frappe._dict(
			linked_doctype="Loan Application", linked_docname=doc.name, kfs_version=stale_version
		)
		acknowledge_kfs_on_signed(log)

		self.assertEqual(frappe.db.get_value("Loan Application", doc.name, "borrower_acknowledged"), 0)

	def test_borrower_acknowledged_is_read_only(self):
		field = frappe.get_meta("Loan Application").get_field("borrower_acknowledged")
		self.assertEqual(field.read_only, 1)

	def test_acknowledge_kfs_requires_kfs_generated(self):
		doc = self.make_application()
		doc.db_set("kfs_valid_till", None)
		self.assertRaises(frappe.ValidationError, acknowledge_kfs, doc.name)

	def test_acknowledge_kfs_rejects_expired_kfs(self):
		doc = self.make_application()
		doc.db_set("kfs_valid_till", add_days(getdate(), -1))
		self.assertRaises(frappe.ValidationError, acknowledge_kfs, doc.name)

	def test_acknowledge_kfs_sets_flag(self):
		doc = self.make_application()
		self.assertFalse(doc.borrower_acknowledged)

		acknowledge_kfs(doc.name)

		self.assertEqual(frappe.db.get_value("Loan Application", doc.name, "borrower_acknowledged"), 1)

	def test_regenerating_kfs_with_changed_terms_resets_acknowledgement(self):
		doc = self.make_application()
		acknowledge_kfs(doc.name)
		self.assertEqual(frappe.db.get_value("Loan Application", doc.name, "borrower_acknowledged"), 1)

		doc.reload()
		doc.loan_amount = 300000
		build_kfs(doc)

		self.assertEqual(doc.borrower_acknowledged, 0)

	def test_resaving_kfs_with_unchanged_terms_keeps_acknowledgement(self):
		doc = self.make_application()
		acknowledge_kfs(doc.name)
		self.assertEqual(frappe.db.get_value("Loan Application", doc.name, "borrower_acknowledged"), 1)

		doc.reload()
		version_before = doc.kfs_version
		build_kfs(doc)

		self.assertEqual(doc.kfs_version, version_before)
		self.assertEqual(doc.borrower_acknowledged, 1)
