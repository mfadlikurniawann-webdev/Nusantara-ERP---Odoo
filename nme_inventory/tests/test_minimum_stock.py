from odoo.tests import new_test_user, tagged

from .common import NmeInventoryCommon


@tagged("post_install", "-at_install")
class TestNmeMinimumStock(NmeInventoryCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.manager = new_test_user(
            cls.env,
            login="nme_stock_manager",
            groups="nme_inventory.nme_group_inventory_manager",
        )
        cls.activity_type = cls.env.ref("nme_inventory.mail_activity_type_low_stock")

    def _low_stock_activities(self, product):
        return self.env["mail.activity"].search(
            [
                ("res_model", "=", "nme.product"),
                ("res_id", "=", product.id),
                ("activity_type_id", "=", self.activity_type.id),
            ]
        )

    def test_below_minimum_flag_and_filter(self):
        self.product.min_qty = 10
        self._receive(self.product, 4, 100.0)
        self.assertTrue(self.product.is_below_min)
        below = self.env["nme.product"].search([("is_below_min", "=", True)])
        self.assertIn(self.product, below)
        self._receive(self.product, 6, 100.0)
        self.assertFalse(self.product.is_below_min)
        self.assertNotIn(
            self.product, self.env["nme.product"].search([("is_below_min", "=", True)])
        )

    def test_cron_warns_managers_once(self):
        self.product.min_qty = 10
        self._receive(self.product, 2, 100.0)
        self.env["nme.product"].sudo()._cron_check_minimum_stock()
        activities = self._low_stock_activities(self.product)
        self.assertIn(self.manager, activities.user_id)

        self.env["nme.product"].sudo()._cron_check_minimum_stock()
        self.assertEqual(self._low_stock_activities(self.product), activities)

    def test_cron_ignores_products_without_minimum(self):
        self._receive(self.product, 2, 100.0)
        self.env["nme.product"].sudo()._cron_check_minimum_stock()
        self.assertFalse(self._low_stock_activities(self.product))
