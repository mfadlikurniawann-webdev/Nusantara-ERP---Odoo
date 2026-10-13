from datetime import timedelta

from odoo import fields
from odoo.exceptions import UserError
from odoo.tests import Form, tagged

from .common import NmeSalesCommon


@tagged("post_install", "-at_install")
class TestNmeSaleFlow(NmeSalesCommon):
    def test_quotation_defaults_and_amounts(self):
        order_form = Form(self.env["nme.sale.order"])
        order_form.partner_id = self.customer
        order_form.warehouse_id = self.warehouse
        with order_form.line_ids.new() as line:
            line.product_id = self.product
            self.assertEqual(line.price_unit, 100000.0)
            self.assertEqual(line.name, "[TST-1] Test Rice")
            line.quantity = 2
            line.discount = 10
        order = order_form.save()

        self.assertEqual(order.payment_term_id, self.term_14)
        self.assertEqual(
            order.validity_date, fields.Date.context_today(order) + timedelta(days=30)
        )
        self.assertEqual(order.line_ids.tax_ids, self.tax_sale)
        self.assertEqual(order.amount_untaxed, 180000.0)
        self.assertEqual(order.amount_tax, 19800.0)
        self.assertEqual(order.amount_total, 199800.0)
        self.assertEqual(order.state, "draft")

    def test_confirm_creates_delivery_and_tracks_delivered_quantity(self):
        order = self._create_order([(self.product, 2), (self.service, 1)])
        order.action_confirm()

        self.assertEqual(order.state, "sale")
        self.assertTrue(order.name.startswith("SO/"))
        delivery = order.picking_ids
        self.assertEqual(len(delivery), 1)
        self.assertEqual(delivery.picking_type, "outgoing")
        self.assertEqual(delivery.origin, order.name)
        # Services are not delivered from the stock.
        self.assertEqual(delivery.move_ids.product_id, self.product)
        self.assertEqual(order.delivery_status, "to_deliver")

        delivery.action_validate()
        product_line = order.line_ids.filtered(
            lambda line: line.product_id == self.product
        )
        self.assertEqual(product_line.qty_delivered, 2)
        self.assertEqual(order.delivery_status, "delivered")
        self.assertEqual(self._qty(self.product), 98)

        returned = self.env["nme.picking"].browse(
            delivery.action_create_return()["res_id"]
        )
        self.assertEqual(returned.sale_id, order)
        returned.action_validate()
        self.assertEqual(product_line.qty_delivered, 0)
        self.assertEqual(order.delivery_status, "to_deliver")

    def test_order_with_services_only_has_no_delivery(self):
        order = self._create_order([(self.service, 1)])
        order.action_confirm()
        self.assertFalse(order.picking_ids)
        self.assertEqual(order.delivery_status, "nothing")

    def test_send_quotation_marks_it_sent(self):
        order = self._create_order()
        action = order.action_quotation_send()
        template = self.env.ref("nme_sales.mail_template_nme_sale_order")
        self.assertEqual(action["context"]["default_template_id"], template.id)

        order.with_context(**action["context"]).message_post(body="Quotation attached")
        self.assertEqual(order.state, "sent")
        order.action_confirm()
        self.assertEqual(order.state, "sale")

    def test_confirmed_lines_are_locked(self):
        order = self._create_order()
        order.action_confirm()
        with self.assertRaises(UserError):
            order.line_ids.quantity = 5
        with self.assertRaises(UserError):
            order.line_ids.unlink()
        with self.assertRaises(UserError):
            order.unlink()

    def test_order_needs_lines_and_valid_transitions(self):
        with self.assertRaises(UserError):
            self._create_order([]).action_confirm()
        order = self._create_order()
        order.action_cancel()
        with self.assertRaises(UserError):
            order.action_confirm()
        order.action_draft()
        order.action_confirm()
        self.assertEqual(order.state, "sale")
