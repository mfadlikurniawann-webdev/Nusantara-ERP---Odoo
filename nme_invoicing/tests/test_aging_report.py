from datetime import timedelta

from odoo.tests import tagged

from .common import NmeInvoicingCommon


@tagged("post_install", "-at_install")
class TestNmeAgingReport(NmeInvoicingCommon):
    def _posted_invoice(self, days_from_today, partner=None, move_type="out_invoice"):
        due = self._today() + timedelta(days=days_from_today)
        invoice = self._create_invoice(
            partner=partner,
            move_type=move_type,
            invoice_date=due - timedelta(days=14),
            invoice_date_due=due,
        )
        invoice.action_post()
        return invoice

    def test_aging_buckets(self):
        not_due = self._posted_invoice(5)
        late_10 = self._posted_invoice(-10)
        late_75 = self._posted_invoice(-75)
        late_120 = self._posted_invoice(-120)
        paid = self._posted_invoice(-40)
        self._pay(paid, paid.amount_total)
        self._pay(late_10, 11000.0)

        Report = self.env["nme.invoice.aging.report"]
        rows = Report.search(
            [
                (
                    "invoice_id",
                    "in",
                    (not_due | late_10 | late_75 | late_120 | paid).ids,
                )
            ]
        )
        by_invoice = {row.invoice_id: row for row in rows}
        self.assertNotIn(paid, by_invoice)
        self.assertEqual(by_invoice[not_due].aging_bucket, "current")
        self.assertEqual(by_invoice[not_due].days_overdue, 0)
        self.assertEqual(by_invoice[late_10].aging_bucket, "1_30")
        self.assertEqual(by_invoice[late_10].days_overdue, 10)
        self.assertEqual(by_invoice[late_10].amount_residual, 100000.0)
        self.assertEqual(by_invoice[late_75].aging_bucket, "61_90")
        self.assertEqual(by_invoice[late_120].aging_bucket, "90_plus")

    def test_receivable_and_payable_are_separated(self):
        receivable = self._posted_invoice(-3)
        payable = self._posted_invoice(-3, partner=self.vendor, move_type="in_invoice")
        Report = self.env["nme.invoice.aging.report"]
        self.assertEqual(
            Report.search([("move_type", "=", "out_invoice")]).invoice_id & payable,
            self.env["nme.invoice"],
        )
        self.assertIn(
            receivable,
            Report.search([("move_type", "=", "out_invoice")]).invoice_id,
        )
