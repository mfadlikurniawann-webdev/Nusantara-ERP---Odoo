from odoo.exceptions import UserError, ValidationError
from odoo.tests import tagged

from .common import NmeInventoryCommon


@tagged("post_install", "-at_install")
class TestNmeStockLedger(NmeInventoryCommon):
    def test_receipt_and_delivery_update_quantity(self):
        receipt = self._receive(self.product, 10, 80000)
        self.assertEqual(receipt.state, "done")
        self.assertTrue(receipt.name.startswith("IN/"))
        self.assertEqual(
            receipt.location_id, self.env.ref("nme_inventory.nme_location_vendors")
        )
        self.assertEqual(self._qty(self.product), 10)

        delivery = self._deliver(self.product, 4)
        self.assertTrue(delivery.name.startswith("OUT/"))
        self.assertTrue(delivery.date_done)
        self.assertEqual(self._qty(self.product), 6)
        self.assertEqual(self._qty(self.product, self.warehouse), 6)
        self.assertEqual(self._qty(self.product, self.warehouse_2), 0)

    def test_stock_cannot_become_negative(self):
        self._receive(self.product, 3, 80000)
        picking = self._create_picking("outgoing", [(self.product, 5)])
        with self.assertRaises(UserError):
            picking.action_validate()
        self.assertEqual(picking.state, "draft")
        self.assertEqual(self._qty(self.product), 3)

    def test_done_moves_are_immutable(self):
        move = self._receive(self.product, 5, 80000).move_ids
        with self.assertRaises(UserError):
            move.quantity = 50
        with self.assertRaises(UserError):
            move.unlink()

    def test_done_transfer_cannot_be_cancelled_or_deleted(self):
        picking = self._receive(self.product, 5, 80000)
        with self.assertRaises(UserError):
            picking.action_cancel()
        with self.assertRaises(UserError):
            picking.unlink()

    def test_draft_transfer_cancel_and_reset(self):
        picking = self._create_picking("incoming", [(self.product, 2, 1000)])
        picking.action_cancel()
        self.assertEqual(picking.state, "cancel")
        self.assertEqual(picking.move_ids.state, "cancel")
        picking.action_set_draft()
        self.assertEqual(picking.move_ids.state, "draft")
        picking.unlink()

    def test_validate_requires_products(self):
        picking = self._create_picking("incoming", [])
        with self.assertRaises(UserError):
            picking.action_validate()

    def test_services_are_not_stocked(self):
        with self.assertRaises(ValidationError):
            self._create_picking("incoming", [(self.service, 1, 1000)])
        self._receive(self.product, 1, 1000)
        with self.assertRaises(ValidationError):
            self.product.type = "service"

    def test_search_on_quantity(self):
        empty = self.env["nme.product"].create({"name": "Empty Shelf"})
        self._receive(self.product, 2, 1000)
        Product = self.env["nme.product"]
        in_stock = Product.search([("qty_available", ">", 0)])
        self.assertIn(self.product, in_stock)
        self.assertNotIn(empty, in_stock)
        self.assertIn(empty, Product.search([("qty_available", "=", 0)]))
