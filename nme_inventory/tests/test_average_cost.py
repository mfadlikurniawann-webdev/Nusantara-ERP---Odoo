from odoo.tests import tagged

from .common import NmeInventoryCommon


@tagged("post_install", "-at_install")
class TestNmeAverageCost(NmeInventoryCommon):
    def test_receipts_update_the_weighted_average(self):
        self._receive(self.product, 10, 100.0)
        self.assertEqual(self.product.avg_cost, 100.0)
        self._receive(self.product, 10, 200.0)
        # (10 x 100 + 10 x 200) / 20
        self.assertEqual(self.product.avg_cost, 150.0)
        self.assertEqual(self.product.stock_value, 20 * 150.0)

    def test_delivery_is_valued_at_average_cost(self):
        self._receive(self.product, 10, 100.0)
        self._receive(self.product, 30, 300.0)
        self.assertEqual(self.product.avg_cost, 250.0)
        move = self._deliver(self.product, 4).move_ids
        self.assertEqual(move.unit_cost, 250.0)
        self.assertEqual(move.value, 1000.0)
        # Goods leaving the stock do not change the average cost.
        self.assertEqual(self.product.avg_cost, 250.0)

    def test_receipt_after_stock_out_restarts_from_new_cost(self):
        self._receive(self.product, 5, 100.0)
        self._deliver(self.product, 5)
        self._receive(self.product, 5, 120.0)
        self.assertEqual(self.product.avg_cost, 120.0)

    def test_internal_transfer_keeps_cost(self):
        self._receive(self.product, 10, 100.0)
        transfer = self._create_picking(
            "internal",
            [(self.product, 4)],
            warehouse_dest_id=self.warehouse_2.id,
        )
        transfer.action_validate()
        self.assertEqual(self.product.avg_cost, 100.0)
        self.assertEqual(self._qty(self.product), 10)

    def test_average_cost_is_per_company(self):
        self._receive(self.product, 10, 100.0)
        other_product = self.product.with_company(self.other_company)
        self.assertEqual(other_product.avg_cost, 0.0)
        self.assertEqual(other_product.qty_available, 0.0)
