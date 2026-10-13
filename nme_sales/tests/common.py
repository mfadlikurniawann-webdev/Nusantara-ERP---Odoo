from odoo import Command

from odoo.addons.nme_inventory.tests.common import NmeInventoryCommon


class NmeSalesCommon(NmeInventoryCommon):
    """A customer, stock of the test product and a helper to build orders."""

    _test_user_groups = (
        *NmeInventoryCommon._test_user_groups,
        "nme_sales.nme_group_sales_manager",
    )

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.term_14 = cls.env.ref("nme_base.nme_payment_term_14_days")
        cls.customer = cls.env["res.partner"].create(
            {
                "name": "Toko Test",
                "nme_is_customer": True,
                "nme_payment_term_id": cls.term_14.id,
            }
        )
        cls.service.list_price = 25000.0
        receipt = cls.env["nme.picking"].create(
            {
                "picking_type": "incoming",
                "warehouse_id": cls.warehouse.id,
                "move_ids": [
                    Command.create(
                        {
                            "product_id": cls.product.id,
                            "quantity": 100,
                            "price_unit": 80000.0,
                        }
                    )
                ],
            }
        )
        receipt.action_validate()

    def _create_order(self, lines=None, partner=None, **values):
        """Create a quotation; ``lines`` is a list of (product, quantity)."""
        lines = lines if lines is not None else [(self.product, 2)]
        return self.env["nme.sale.order"].create(
            {
                "partner_id": (partner or self.customer).id,
                "warehouse_id": self.warehouse.id,
                "line_ids": [
                    Command.create({"product_id": product.id, "quantity": qty})
                    for product, qty in lines
                ],
                **values,
            }
        )
