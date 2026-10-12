from datetime import date

from psycopg2 import IntegrityError

from odoo.tests import tagged
from odoo.tools import mute_logger

from .common import NmeBaseCommon


@tagged("post_install", "-at_install")
class TestNmeTaxPaymentTerm(NmeBaseCommon):
    def test_taxes_apply_on_the_same_untaxed_base(self):
        regional_tax = self.env["nme.tax"].create(
            {"name": "Regional 1.5%", "amount": 1.5, "company_id": self.company.id}
        )
        taxes = self.tax_sale | regional_tax
        # 11% of 1,000 plus 1.5% of 1,000 (not compounded).
        self.assertAlmostEqual(taxes._get_tax_amount(1000.0, self.currency), 125.0)
        self.assertEqual(self.env["nme.tax"]._get_tax_amount(1000.0, self.currency), 0)

    @mute_logger("odoo.sql_db")
    def test_tax_rate_must_be_a_percentage(self):
        with self.assertRaises(IntegrityError):
            self.env["nme.tax"].create({"name": "Too much", "amount": 150})

    def test_payment_term_due_date(self):
        term_30 = self.env.ref("nme_base.nme_payment_term_30_days")
        immediate = self.env.ref("nme_base.nme_payment_term_immediate")
        self.assertEqual(term_30._get_due_date(date(2026, 1, 15)), date(2026, 2, 14))
        self.assertEqual(immediate._get_due_date(date(2026, 1, 15)), date(2026, 1, 15))

    @mute_logger("odoo.sql_db")
    def test_payment_term_days_cannot_be_negative(self):
        with self.assertRaises(IntegrityError):
            self.env["nme.payment.term"].create({"name": "Bad", "days": -1})
