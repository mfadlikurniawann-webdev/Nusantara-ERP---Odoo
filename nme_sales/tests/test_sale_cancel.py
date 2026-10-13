from odoo.exceptions import UserError
from odoo.tests import Form, tagged

from .common import NmeSalesCommon


@tagged("post_install", "-at_install")
class TestNmeSaleCancel(NmeSalesCommon):
    def test_cancel_confirmed_order_cancels_its_delivery(self):
        order = self._create_order()
        order.action_confirm()
        order.action_cancel()
        self.assertEqual(order.state, "cancel")
        self.assertEqual(order.picking_ids.state, "cancel")

    def test_delivered_goods_must_be_returned_before_cancelling(self):
        order = self._create_order()
        order.action_confirm()
        order.picking_ids.action_validate()
        with self.assertRaises(UserError):
            order.action_cancel()

        returned = self.env["nme.picking"].browse(
            order.picking_ids.action_create_return()["res_id"]
        )
        returned.action_validate()
        order.action_cancel()
        self.assertEqual(order.state, "cancel")
        self.assertEqual(self._qty(self.product), 100)

    def test_cancel_wizard_records_the_reason(self):
        order = self._create_order()
        action = order.action_open_cancel_wizard()
        wizard_form = Form(
            self.env[action["res_model"]].with_context(**action["context"])
        )
        wizard_form.reason = "Customer found a cheaper supplier"
        wizard_form.save().action_confirm()
        self.assertEqual(order.state, "cancel")
        self.assertEqual(order.cancel_reason, "Customer found a cheaper supplier")
        self.assertIn("cheaper supplier", order.message_ids[0].body)

    def test_reconfirm_after_reset_creates_a_new_delivery(self):
        order = self._create_order()
        order.action_confirm()
        order.action_cancel()
        order.action_draft()
        order.action_confirm()
        self.assertEqual(len(order.picking_ids), 2)
        self.assertEqual(
            order.picking_ids.mapped("state").count("draft"),
            1,
        )
