from odoo import Command

from odoo.addons.nme_base.tests.common import NmeBaseCommon


class NmeInventoryCommon(NmeBaseCommon):
    """Warehouses, a stockable product and helpers to move stock in tests."""

    _test_user_groups = (
        *NmeBaseCommon._test_user_groups,
        "nme_inventory.nme_group_inventory_manager",
    )

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        Warehouse = cls.env["nme.warehouse"]
        cls.warehouse = Warehouse.create(
            {"name": "Test Surabaya", "code": "TSBY", "company_id": cls.company.id}
        )
        cls.warehouse_2 = Warehouse.create(
            {"name": "Test Sidoarjo", "code": "TSDA", "company_id": cls.company.id}
        )
        cls.stock = cls.warehouse.lot_stock_id
        cls.stock_2 = cls.warehouse_2.lot_stock_id
        cls.reason = cls.env.ref("nme_inventory.nme_adjustment_reason_count")
        cls.service = cls.env["nme.product"].create(
            {"name": "Test Delivery Fee", "type": "service"}
        )
        cls.partner_vendor = cls.env["res.partner"].create(
            {"name": "Test Vendor", "nme_is_vendor": True}
        )
        cls.partner_customer = cls.env["res.partner"].create(
            {"name": "Test Customer", "nme_is_customer": True}
        )

    def _create_picking(self, picking_type, lines, warehouse=None, **values):
        """Create a draft transfer; ``lines`` is a list of (product, qty[, cost])."""
        moves = []
        for product, qty, *cost in lines:
            move = {"product_id": product.id, "quantity": qty}
            if cost:
                move["price_unit"] = cost[0]
            moves.append(Command.create(move))
        return self.env["nme.picking"].create(
            {
                "picking_type": picking_type,
                "warehouse_id": (warehouse or self.warehouse).id,
                "move_ids": moves,
                **values,
            }
        )

    def _receive(self, product, qty, cost, warehouse=None):
        picking = self._create_picking(
            "incoming",
            [(product, qty, cost)],
            warehouse=warehouse,
            partner_id=self.partner_vendor.id,
        )
        picking.action_validate()
        return picking

    def _deliver(self, product, qty, warehouse=None):
        picking = self._create_picking(
            "outgoing",
            [(product, qty)],
            warehouse=warehouse,
            partner_id=self.partner_customer.id,
        )
        picking.action_validate()
        return picking

    def _qty(self, product, warehouse=None):
        context = {"warehouse_id": warehouse.id} if warehouse else {}
        return product.with_context(**context).qty_available
