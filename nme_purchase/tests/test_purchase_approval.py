from odoo.exceptions import UserError
from odoo.tests import new_test_user, tagged

from .common import NmePurchaseCommon


@tagged("post_install", "-at_install")
class TestNmePurchaseApproval(NmePurchaseCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.buyer = new_test_user(
            cls.env, login="nme_buyer", groups="nme_purchase.nme_group_purchase_user"
        )
        cls.purchase_manager = new_test_user(
            cls.env,
            login="nme_purchase_manager",
            groups="nme_purchase.nme_group_purchase_manager",
        )
        cls.activity_type = cls.env.ref("nme_purchase.mail_activity_type_po_approval")

    def _big_po_by_buyer(self):
        # 15 x 80,000 + 11% = 1,332,000 >= 1,000,000
        return (
            self.env["nme.purchase.order"]
            .with_user(self.buyer)
            .create(
                {
                    "partner_id": self.vendor.id,
                    "warehouse_id": self.warehouse.id,
                    "line_ids": [
                        (0, 0, {"product_id": self.product.id, "quantity": 15})
                    ],
                }
            )
        )

    def _approval_activities(self, po):
        return po.activity_ids.filtered(
            lambda a: a.activity_type_id == self.activity_type
        )

    def test_large_order_by_buyer_waits_for_approval(self):
        po = self._big_po_by_buyer()
        self.assertTrue(po.approval_required)
        po.action_confirm()
        self.assertEqual(po.state, "to_approve")
        self.assertFalse(po.picking_ids)
        self.assertIn(self.purchase_manager, self._approval_activities(po).user_id)
        with self.assertRaises(UserError):
            po.with_user(self.buyer).line_ids.quantity = 1
        with self.assertRaises(UserError):
            po.with_user(self.buyer).action_approve()

        po.with_user(self.purchase_manager).action_approve()
        self.assertEqual(po.state, "purchase")
        self.assertEqual(po.approved_by_id, self.purchase_manager)
        self.assertTrue(po.approval_date)
        self.assertTrue(po.picking_ids)
        self.assertFalse(self._approval_activities(po))

    def test_manager_rejects_order(self):
        po = self._big_po_by_buyer()
        po.action_confirm()
        po.with_user(self.purchase_manager).action_reject()
        self.assertEqual(po.state, "draft")
        self.assertFalse(self._approval_activities(po))
        self.assertIn("Rejected", po.message_ids[0].body)

    def test_manager_confirms_large_order_directly(self):
        po = self._create_po([(self.product, 15)])
        self.assertTrue(po.approval_required)
        po.action_confirm()
        self.assertEqual(po.state, "purchase")
        self.assertEqual(po.approved_by_id, self.env.user)

    def test_small_order_and_disabled_threshold(self):
        small = self._big_po_by_buyer()
        small.line_ids.quantity = 1
        small.action_confirm()
        self.assertEqual(small.state, "purchase")

        # Disabling the approval is a settings change, done as administrator.
        self.company.sudo().nme_po_approval_amount = 0
        big = self._big_po_by_buyer()
        self.assertFalse(big.approval_required)
        big.action_confirm()
        self.assertEqual(big.state, "purchase")
