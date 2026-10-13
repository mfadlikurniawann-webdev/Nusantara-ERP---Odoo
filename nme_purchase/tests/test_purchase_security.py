from odoo.exceptions import AccessError
from odoo.tests import new_test_user, tagged
from odoo.tools import mute_logger

from .common import NmePurchaseCommon


@tagged("post_install", "-at_install")
class TestNmePurchaseSecurity(NmePurchaseCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.buyer = new_test_user(
            cls.env,
            login="nme_sec_buyer",
            groups="nme_purchase.nme_group_purchase_user",
        )
        cls.storekeeper = new_test_user(
            cls.env,
            login="nme_sec_storekeeper_po",
            groups="nme_inventory.nme_group_inventory_user",
        )
        cls.internal_user = new_test_user(
            cls.env, login="nme_sec_internal_po", groups="base.group_user"
        )

    def test_buyer_creates_and_confirms_with_receipt(self):
        po = (
            self.env["nme.purchase.order"]
            .with_user(self.buyer)
            .create(
                {
                    "partner_id": self.vendor.id,
                    "warehouse_id": self.warehouse.id,
                    "line_ids": [
                        (0, 0, {"product_id": self.product.id, "quantity": 2})
                    ],
                }
            )
        )
        po.action_confirm()
        self.assertEqual(po.with_user(self.buyer).picking_ids.state, "draft")

    def test_storekeeper_receives_purchase_orders(self):
        po = self._create_po()
        po.action_confirm()
        receipt = po.picking_ids.with_user(self.storekeeper)
        self.assertEqual(receipt.purchase_id.name, po.name)
        receipt.action_validate()
        self.assertEqual(po.line_ids.qty_received, 5)

    @mute_logger("odoo.addons.base.models.ir_access")
    def test_internal_user_cannot_access_purchases(self):
        po = self._create_po()
        with self.assertRaises(AccessError):
            po.with_user(self.internal_user).read(["name"])
