from datetime import timedelta

from odoo.exceptions import UserError
from odoo.tests import tagged

from .common import NmeInvoicingCommon


@tagged("post_install", "-at_install")
class TestNmeInvoiceFlow(NmeInvoicingCommon):
    def test_invoice_follows_the_delivered_quantity(self):
        order = self._create_order([(self.product, 2), (self.service, 1)])
        order.action_confirm()
        # Services are invoiced as ordered, goods once delivered.
        self.assertEqual(order.invoice_status, "to_invoice")
        order.action_create_invoice()
        first = order.invoice_ids
        self.assertEqual(first.line_ids.product_id, self.service)
        self.assertEqual(first.payment_term_id, self.term_14)
        self.assertEqual(order.invoice_status, "nothing")

        order.picking_ids.action_validate()
        self.assertEqual(order.invoice_status, "to_invoice")
        order.action_create_invoice()
        second = order.invoice_ids - first
        self.assertEqual(second.line_ids.product_id, self.product)
        self.assertEqual(second.line_ids.quantity, 2)
        self.assertEqual(second.line_ids.tax_ids, self.tax_sale)
        self.assertEqual(order.invoice_status, "invoiced")
        self.assertEqual(order.invoice_count, 2)
        with self.assertRaises(UserError):
            order.action_create_invoice()

    def test_numbering_happens_on_post_without_gaps(self):
        first = self._create_invoice()
        self.assertEqual(first.display_name, "Draft Invoice")
        draft = self._create_invoice()
        draft.unlink()

        first.action_post()
        self.assertTrue(first.name.startswith("INV/"))
        second = self._create_invoice()
        second.action_post()
        number_1 = int(first.name.split("/")[-1])
        number_2 = int(second.name.split("/")[-1])
        self.assertEqual(number_2, number_1 + 1)
        self.assertEqual(first.invoice_date, self._today())

        # Reset and repost keeps the number; numbered invoices are not deleted.
        first.action_draft()
        first.action_post()
        self.assertEqual(int(first.name.split("/")[-1]), number_1)
        first.action_draft()
        with self.assertRaises(UserError):
            first.unlink()

    def test_due_date_from_payment_terms(self):
        invoice = self._create_invoice(invoice_date=self._today() - timedelta(days=20))
        self.assertEqual(invoice.payment_term_id, self.term_14)
        self.assertEqual(invoice.invoice_date_due, self._today() - timedelta(days=6))
        self.assertFalse(invoice.is_overdue)
        invoice.action_post()
        self.assertTrue(invoice.is_overdue)

    def test_overdue_cron_warns_once(self):
        activity_type = self.env.ref("nme_invoicing.mail_activity_type_overdue")
        invoice = self._create_invoice(
            invoice_date=self._today() - timedelta(days=10),
            invoice_date_due=self._today() + timedelta(days=5),
        )
        invoice.action_post()
        self.assertFalse(invoice.is_overdue)
        # Time passes: the due date is now in the past.
        invoice.sudo().write({"invoice_date_due": self._today() - timedelta(days=1)})
        invoice.sudo().is_overdue = False
        self.env["nme.invoice"].sudo()._cron_update_overdue()
        self.assertTrue(invoice.is_overdue)
        activities = invoice.activity_ids.filtered(
            lambda a: a.activity_type_id == activity_type
        )
        self.assertEqual(len(activities), 1)
        self.env["nme.invoice"].sudo()._cron_update_overdue()
        self.assertEqual(
            len(
                invoice.activity_ids.filtered(
                    lambda a: a.activity_type_id == activity_type
                )
            ),
            1,
        )

    def test_vendor_bill_follows_the_received_quantity(self):
        po = self._create_po([(self.product, 4, 80000.0)], partner_ref="V-123")
        po.action_confirm()
        with self.assertRaises(UserError):
            po.action_create_bill()
        po.picking_ids.action_validate()
        po.action_create_bill()
        bill = po.invoice_ids
        self.assertEqual(bill.move_type, "in_invoice")
        self.assertEqual(bill.ref, "V-123")
        self.assertEqual(bill.payment_term_id, self.term_30)
        self.assertEqual(bill.line_ids.tax_ids, self.tax_purchase)
        bill.action_post()
        self.assertTrue(bill.name.startswith("BILL/"))
        self.assertEqual(po.invoice_status, "invoiced")

    def test_orders_with_invoices_cannot_be_cancelled(self):
        order = self._create_order([(self.service, 1)])
        order.action_confirm()
        order.action_create_invoice()
        with self.assertRaises(UserError):
            order.action_cancel()
        order.invoice_ids.action_cancel()
        order.action_cancel()
        self.assertEqual(order.state, "cancel")

    def test_posted_lines_are_locked_and_report_renders(self):
        invoice = self._create_invoice()
        invoice.action_post()
        with self.assertRaises(UserError):
            invoice.line_ids.price_unit = 1
        html, _format = self.env["ir.actions.report"]._render_qweb_html(
            "nme_invoicing.report_nme_invoice", invoice.ids
        )
        self.assertIn(invoice.name, html.decode())
        template = self.env.ref("nme_invoicing.mail_template_nme_invoice")
        subject = template._render_field("subject", invoice.ids)[invoice.id]
        self.assertIn(invoice.name, subject)
