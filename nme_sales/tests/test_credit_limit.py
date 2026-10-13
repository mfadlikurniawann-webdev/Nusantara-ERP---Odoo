from odoo.exceptions import UserError
from odoo.tests import new_test_user, tagged

from .common import NmeSalesCommon


@tagged("post_install", "-at_install")
class TestNmeCreditLimit(NmeSalesCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.salesman = new_test_user(
            cls.env, login="nme_salesman", groups="nme_sales.nme_group_sales_user"
        )
        cls.salesman_2 = new_test_user(
            cls.env, login="nme_salesman_2", groups="nme_sales.nme_group_sales_user"
        )
        cls.customer.write({"nme_credit_policy": "block", "nme_credit_limit": 300000})

    def _order_as(self, user, qty):
        return (
            self.env["nme.sale.order"]
            .with_user(user)
            .create(
                {
                    "partner_id": self.customer.id,
                    "warehouse_id": self.warehouse.id,
                    "line_ids": [
                        (0, 0, {"product_id": self.product.id, "quantity": qty})
                    ],
                }
            )
        )

    def test_block_policy_stops_salesman_but_not_manager(self):
        # 3 x 100,000 + 11% VAT = 333,000 > 300,000
        order = self._order_as(self.salesman, 3)
        self.assertTrue(order.credit_warning)
        with self.assertRaises(UserError):
            order.action_confirm()
        self.assertEqual(order.state, "draft")

        # The test user is a sales manager: confirming is allowed and logged.
        self.env["nme.sale.order"].browse(order.id).action_confirm()
        self.assertEqual(order.state, "sale")
        self.assertIn("credit limit", order.message_ids[0].body)

    def test_warning_policy_allows_confirmation(self):
        self.customer.nme_credit_policy = "warning"
        order = self._order_as(self.salesman, 3)
        order.action_confirm()
        self.assertEqual(order.state, "sale")
        self.assertIn("credit limit", order.message_ids[0].body)

    def test_exposure_counts_orders_of_other_salespeople(self):
        first = self._order_as(self.salesman, 2)  # 222,000
        first.action_confirm()
        self.assertEqual(self.customer.nme_credit_exposure, 222000.0)

        # 222,000 + 111,000 > 300,000, although salesman_2 cannot read the
        # first order.
        second = self._order_as(self.salesman_2, 1)
        self.assertFalse(
            self.env["nme.sale.order"]
            .with_user(self.salesman_2)
            .search([("id", "=", first.id)])
        )
        with self.assertRaises(UserError):
            second.action_confirm()

    def test_no_limit_policy(self):
        self.customer.nme_credit_policy = "none"
        order = self._order_as(self.salesman, 50)
        self.assertFalse(order.credit_warning)
        order.action_confirm()
        self.assertEqual(order.state, "sale")
