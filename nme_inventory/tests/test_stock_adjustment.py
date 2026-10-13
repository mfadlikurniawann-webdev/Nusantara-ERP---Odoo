from odoo import Command
from odoo.tests import Form, tagged

from .common import NmeInventoryCommon


@tagged("post_install", "-at_install")
class TestNmeStockAdjustment(NmeInventoryCommon):
    def _adjustment(self, lines):
        return self.env["nme.stock.adjustment"].create(
            {
                "warehouse_id": self.warehouse.id,
                "reason_id": self.reason.id,
                "line_ids": [
                    Command.create(
                        {
                            "product_id": product.id,
                            "counted_qty": qty,
                            "unit_cost": cost,
                        }
                    )
                    for product, qty, cost in lines
                ],
            }
        )

    def test_positive_and_negative_differences(self):
        sugar = self.env["nme.product"].create({"name": "Sugar"})
        self._receive(self.product, 10, 100.0)
        adjustment = self._adjustment([(self.product, 7, 0.0), (sugar, 5, 50.0)])
        self.assertEqual(adjustment.line_ids[0].difference_qty, -3)
        adjustment.action_validate()

        self.assertEqual(adjustment.state, "done")
        self.assertTrue(adjustment.name.startswith("ADJ/"))
        self.assertEqual(self._qty(self.product), 7)
        self.assertEqual(self._qty(sugar), 5)
        self.assertEqual(sugar.avg_cost, 50.0)
        loss = self.env.ref("nme_inventory.nme_location_inventory_loss")
        self.assertEqual(
            adjustment.move_ids.filtered(
                lambda m: m.product_id == self.product
            ).location_dest_id,
            loss,
        )

    def test_difference_uses_stock_at_validation_time(self):
        adjustment = self._adjustment([(self.product, 10, 100.0)])
        self.assertEqual(adjustment.line_ids.theoretical_qty, 0)
        # Goods arrive between the count and the validation.
        self._receive(self.product, 4, 100.0)
        adjustment.action_validate()
        self.assertEqual(adjustment.line_ids.theoretical_qty, 4)
        self.assertEqual(adjustment.line_ids.difference_qty, 6)
        self.assertEqual(self._qty(self.product), 10)

    def test_load_products_in_stock(self):
        self._receive(self.product, 8, 100.0)
        adjustment = self._adjustment([])
        adjustment.action_load_products()
        self.assertEqual(adjustment.line_ids.product_id, self.product)
        self.assertEqual(adjustment.line_ids.counted_qty, 8)
        self.assertEqual(adjustment.line_ids.difference_qty, 0)

    def test_quick_adjust_wizard(self):
        self._receive(self.product, 5, 100.0)
        wizard_form = Form(
            self.env["nme.product.quick.adjust"].with_context(active_id=self.product.id)
        )
        wizard_form.warehouse_id = self.warehouse
        wizard_form.counted_qty = 9
        wizard_form.reason_id = self.reason
        self.assertEqual(wizard_form.current_qty, 5)
        self.assertEqual(wizard_form.unit_cost, 100.0)
        wizard_form.save().action_apply()
        self.assertEqual(self._qty(self.product), 9)
