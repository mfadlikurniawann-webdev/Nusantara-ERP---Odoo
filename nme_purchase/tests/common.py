from odoo import Command

from odoo.addons.nme_inventory.tests.common import NmeInventoryCommon


class NmePurchaseCommon(NmeInventoryCommon):
    """A vendor with payment terms and a helper to build purchase orders."""

    _test_user_groups = (
        *NmeInventoryCommon._test_user_groups,
        "nme_purchase.nme_group_purchase_manager",
    )

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.term_30 = cls.env.ref("nme_base.nme_payment_term_30_days")
        cls.vendor = cls.env["res.partner"].create(
            {
                "name": "Pabrik Test",
                "nme_is_vendor": True,
                "nme_vendor_payment_term_id": cls.term_30.id,
            }
        )
        cls.company.nme_po_approval_amount = 1000000.0

    def _create_po(self, lines=None, **values):
        """Create an RFQ; ``lines`` is a list of (product, quantity[, price])."""
        lines = lines if lines is not None else [(self.product, 5)]
        commands = []
        for product, qty, *price in lines:
            line = {"product_id": product.id, "quantity": qty}
            if price:
                line["price_unit"] = price[0]
            commands.append(Command.create(line))
        return self.env["nme.purchase.order"].create(
            {
                "partner_id": self.vendor.id,
                "warehouse_id": self.warehouse.id,
                "line_ids": commands,
                **values,
            }
        )
