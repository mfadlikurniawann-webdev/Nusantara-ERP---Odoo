from odoo.exceptions import UserError
from odoo.tests import Form, tagged

from .common import NmePurchaseCommon


@tagged("post_install", "-at_install")
class TestNmePurchaseFlow(NmePurchaseCommon):
    def test_rfq_defaults_and_amounts(self):
        po_form = Form(self.env["nme.purchase.order"])
        po_form.partner_id = self.vendor
        po_form.warehouse_id = self.warehouse
        with po_form.line_ids.new() as line:
            line.product_id = self.product
            self.assertEqual(line.price_unit, 80000.0)
            line.quantity = 3
        po = po_form.save()
        self.assertEqual(po.payment_term_id, self.term_30)
        self.assertEqual(po.line_ids.tax_ids, self.tax_purchase)
        self.assertEqual(po.amount_untaxed, 240000.0)
        self.assertEqual(po.amount_total, 266400.0)
        self.assertFalse(po.approval_required)

    def test_receipt_updates_quantity_and_average_cost(self):
        po = self._create_po([(self.product, 5, 100000.0)])
        po.line_ids.discount = 10
        po.action_confirm()
        self.assertEqual(po.state, "purchase")
        self.assertTrue(po.name.startswith("PO/"))
        receipt = po.picking_ids
        self.assertEqual(receipt.picking_type, "incoming")
        self.assertEqual(receipt.origin, po.name)
        self.assertEqual(po.receipt_status, "to_receive")

        receipt.action_validate()
        self.assertEqual(po.line_ids.qty_received, 5)
        self.assertEqual(po.receipt_status, "received")
        # The net price (after discount, without taxes) feeds the average cost.
        self.assertEqual(self.product.avg_cost, 90000.0)
        self.assertEqual(self._qty(self.product), 5)

    def test_return_to_vendor_reduces_received_quantity(self):
        po = self._create_po()
        po.action_confirm()
        po.picking_ids.action_validate()
        returned = self.env["nme.picking"].browse(
            po.picking_ids.action_create_return()["res_id"]
        )
        self.assertEqual(returned.purchase_id, po)
        returned.action_validate()
        self.assertEqual(po.line_ids.qty_received, 0)
        self.assertEqual(po.receipt_status, "to_receive")

    def test_services_are_not_received(self):
        po = self._create_po([(self.service, 1, 50000.0)])
        po.action_confirm()
        self.assertFalse(po.picking_ids)
        self.assertEqual(po.receipt_status, "nothing")

    def test_send_rfq_marks_it_sent(self):
        po = self._create_po()
        action = po.action_rfq_send()
        po.with_context(**action["context"]).message_post(body="RFQ attached")
        self.assertEqual(po.state, "sent")

    def test_cancel_rules(self):
        po = self._create_po()
        po.action_confirm()
        po.picking_ids.action_validate()
        with self.assertRaises(UserError):
            po.action_cancel()
        returned = self.env["nme.picking"].browse(
            po.picking_ids.action_create_return()["res_id"]
        )
        returned.action_validate()
        po.action_cancel()
        self.assertEqual(po.state, "cancel")

        other = self._create_po()
        other.action_confirm()
        other.action_cancel()
        self.assertEqual(other.picking_ids.state, "cancel")
        other.action_draft()
        self.assertEqual(other.state, "draft")

    def test_confirmed_lines_are_locked(self):
        po = self._create_po()
        po.action_confirm()
        with self.assertRaises(UserError):
            po.line_ids.price_unit = 1
        with self.assertRaises(UserError):
            self._create_po([]).action_confirm()

    def test_purchase_order_report_renders(self):
        po = self._create_po()
        html, _format = self.env["ir.actions.report"]._render_qweb_html(
            "nme_purchase.report_nme_purchase_order", po.ids
        )
        self.assertIn(po.name, html.decode())
        self.assertIn("Request for Quotation", html.decode())
