from odoo.exceptions import UserError, ValidationError
from odoo.tests import tagged

from .common import NmeInventoryCommon


@tagged("post_install", "-at_install")
class TestNmeTransferReturn(NmeInventoryCommon):
    def test_transfer_between_warehouses(self):
        self._receive(self.product, 10, 100.0)
        transfer = self._create_picking(
            "internal",
            [(self.product, 4)],
            warehouse_dest_id=self.warehouse_2.id,
        )
        self.assertEqual(transfer.location_dest_id, self.stock_2)
        transfer.action_validate()
        self.assertTrue(transfer.name.startswith("INT/"))
        self.assertEqual(self._qty(self.product, self.warehouse), 6)
        self.assertEqual(self._qty(self.product, self.warehouse_2), 4)
        self.assertEqual(self._qty(self.product), 10)

    def test_transfer_needs_another_warehouse(self):
        with self.assertRaises(ValidationError):
            self._create_picking("internal", [], warehouse_dest_id=self.warehouse.id)
        with self.assertRaises(ValidationError):
            self._create_picking("internal", [])

    def test_return_of_delivery_restores_stock_at_original_cost(self):
        self._receive(self.product, 10, 100.0)
        delivery = self._deliver(self.product, 4)
        self._receive(self.product, 10, 400.0)

        action = delivery.action_create_return()
        returned = self.env["nme.picking"].browse(action["res_id"])
        self.assertEqual(returned.picking_type, "incoming")
        self.assertEqual(returned.location_id, delivery.location_dest_id)
        self.assertEqual(returned.location_dest_id, delivery.location_id)
        self.assertEqual(returned.move_ids.origin_returned_move_id, delivery.move_ids)
        self.assertEqual(delivery.return_count, 1)

        returned.action_validate()
        self.assertEqual(self._qty(self.product), 20)
        self.assertEqual(returned.move_ids.unit_cost, 100.0)

        with self.assertRaises(UserError):
            delivery.action_create_return()

    def test_return_of_receipt_goes_back_to_vendor(self):
        receipt = self._receive(self.product, 5, 100.0)
        action = receipt.action_create_return()
        returned = self.env["nme.picking"].browse(action["res_id"])
        self.assertEqual(returned.picking_type, "outgoing")
        self.assertEqual(returned.location_dest_id, receipt.location_id)
        returned.action_validate()
        self.assertEqual(self._qty(self.product), 0)

    def test_only_done_transfers_can_be_returned(self):
        picking = self._create_picking("incoming", [(self.product, 1, 1.0)])
        with self.assertRaises(UserError):
            picking.action_create_return()
