from odoo.tests import tagged

from .common import NmeInvoicingCommon


@tagged("post_install", "-at_install")
class TestNmeCreditExposure(NmeInvoicingCommon):
    def _exposure(self):
        # Non-stored computed field: read a fresh value after each change.
        self.customer.invalidate_recordset(["nme_credit_exposure"])
        return self.customer.nme_credit_exposure

    def test_exposure_moves_from_orders_to_open_invoices(self):
        order = self._confirmed_delivered_order(qty=2)  # 222,000
        self.assertEqual(self._exposure(), 222000.0)

        order.action_create_invoice()
        invoice = order.invoice_ids
        # Invoiced but not paid: still owed.
        self.assertEqual(self._exposure(), 222000.0)
        invoice.action_post()
        self.assertEqual(self._exposure(), 222000.0)

        self._pay(invoice, 100000.0)
        self.assertEqual(self._exposure(), 122000.0)
        self._pay(invoice, 122000.0)
        self.assertEqual(self._exposure(), 0.0)

    def test_manual_invoices_count_in_the_exposure(self):
        invoice = self._create_invoice()  # 111,000
        invoice.action_post()
        self.assertEqual(self._exposure(), 111000.0)
        invoice.action_cancel()
        self.assertEqual(self._exposure(), 0.0)

    def test_unpaid_invoices_block_new_orders(self):
        self.customer.write(
            {"nme_credit_policy": "warning", "nme_credit_limit": 150000}
        )
        invoice = self._create_invoice()
        invoice.action_post()
        order = self._create_order([(self.product, 1)])
        # 111,000 due + 111,000 new order > 150,000
        self.assertTrue(order.credit_warning)
        self._pay(invoice, 111000.0)
        order.invalidate_recordset(["credit_warning"])
        self.assertFalse(order.credit_warning)
