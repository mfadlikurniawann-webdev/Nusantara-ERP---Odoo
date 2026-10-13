from odoo import Command
from odoo.exceptions import AccessError, UserError
from odoo.tests import new_test_user, tagged
from odoo.tools import mute_logger

from .common import NmeInventoryCommon


@tagged("post_install", "-at_install")
class TestNmeStockSecurity(NmeInventoryCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.inventory_user = new_test_user(
            cls.env,
            login="nme_stock_user",
            groups="nme_inventory.nme_group_inventory_user",
        )
        cls.internal_user = new_test_user(
            cls.env, login="nme_plain_user", groups="base.group_user"
        )

    def test_inventory_user_moves_stock_but_cannot_validate_adjustments(self):
        Picking = self.env["nme.picking"].with_user(self.inventory_user)
        picking = Picking.create(
            {
                "picking_type": "incoming",
                "warehouse_id": self.warehouse.id,
                "move_ids": [
                    Command.create(
                        {"product_id": self.product.id, "quantity": 3, "price_unit": 10}
                    )
                ],
            }
        )
        # Validating updates the average cost although the user cannot edit products.
        picking.action_validate()
        self.assertEqual(self.product.avg_cost, 10)

        adjustment = (
            self.env["nme.stock.adjustment"]
            .with_user(self.inventory_user)
            .create(
                {
                    "warehouse_id": self.warehouse.id,
                    "reason_id": self.reason.id,
                    "line_ids": [
                        Command.create(
                            {"product_id": self.product.id, "counted_qty": 1}
                        )
                    ],
                }
            )
        )
        with self.assertRaises(UserError):
            adjustment.action_validate()

    @mute_logger("odoo.addons.base.models.ir_access")
    def test_internal_user_cannot_create_transfers(self):
        with self.assertRaises(AccessError):
            self.env["nme.picking"].with_user(self.internal_user).create(
                {"picking_type": "incoming", "warehouse_id": self.warehouse.id}
            )

    def test_transfers_of_other_companies_are_hidden(self):
        other_warehouse = self.env["nme.warehouse"].search(
            [("company_id", "=", self.other_company.id)]
        )
        self.assertTrue(other_warehouse, "Each new company gets a warehouse.")
        other_picking = (
            self.env["nme.picking"]
            .with_company(self.other_company)
            .create({"picking_type": "incoming", "warehouse_id": other_warehouse.id})
        )
        Picking = self.env["nme.picking"].with_user(self.inventory_user)
        self.assertFalse(Picking.search([("id", "=", other_picking.id)]))
