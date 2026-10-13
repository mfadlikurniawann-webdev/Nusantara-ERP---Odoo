from odoo.exceptions import AccessError
from odoo.tests import new_test_user, tagged
from odoo.tools import mute_logger

from .common import NmeSalesCommon


@tagged("post_install", "-at_install")
class TestNmeSaleSecurity(NmeSalesCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.salesman = new_test_user(
            cls.env, login="nme_sec_salesman", groups="nme_sales.nme_group_sales_user"
        )
        cls.salesman_2 = new_test_user(
            cls.env,
            login="nme_sec_salesman_2",
            groups="nme_sales.nme_group_sales_user",
        )
        cls.storekeeper = new_test_user(
            cls.env,
            login="nme_sec_storekeeper",
            groups="nme_inventory.nme_group_inventory_user",
        )

    def _order_of(self, user):
        return (
            self.env["nme.sale.order"]
            .with_user(user)
            .create(
                {
                    "partner_id": self.customer.id,
                    "warehouse_id": self.warehouse.id,
                    "line_ids": [
                        (0, 0, {"product_id": self.product.id, "quantity": 1})
                    ],
                }
            )
        )

    def test_salesman_only_sees_own_orders(self):
        own = self._order_of(self.salesman)
        other = self._order_of(self.salesman_2)
        visible = (
            self.env["nme.sale.order"]
            .with_user(self.salesman)
            .search([("id", "in", (own | other).ids)])
        )
        self.assertEqual(visible, own)
        with self.assertRaises(AccessError), mute_logger(
            "odoo.addons.base.models.ir_access"
        ):
            other.with_user(self.salesman).line_ids.read(["quantity"])

    def test_salesman_confirms_and_reads_the_delivery(self):
        order = self._order_of(self.salesman)
        order.action_confirm()
        delivery = order.with_user(self.salesman).picking_ids
        self.assertEqual(len(delivery), 1)
        self.assertEqual(delivery.state, "draft")

    def test_storekeeper_reads_orders_and_validates_deliveries(self):
        order = self._order_of(self.salesman)
        order.action_confirm()
        delivery = order.picking_ids.with_user(self.storekeeper)
        self.assertEqual(delivery.sale_id.name, order.name)
        delivery.action_validate()
        self.assertEqual(order.line_ids.qty_delivered, 1)

    def test_orders_of_other_companies_are_hidden(self):
        other_warehouse = self.env["nme.warehouse"].search(
            [("company_id", "=", self.other_company.id)]
        )
        other_order = (
            self.env["nme.sale.order"]
            .with_company(self.other_company)
            .create(
                {
                    "partner_id": self.customer.id,
                    "warehouse_id": other_warehouse.id,
                    "company_id": self.other_company.id,
                }
            )
        )
        manager = new_test_user(
            self.env,
            login="nme_sec_manager",
            groups="nme_sales.nme_group_sales_manager",
        )
        self.assertFalse(
            self.env["nme.sale.order"]
            .with_user(manager)
            .search([("id", "=", other_order.id)])
        )
