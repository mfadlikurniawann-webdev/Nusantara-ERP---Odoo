from odoo.exceptions import AccessError
from odoo.tests import new_test_user, tagged
from odoo.tools import mute_logger

from .common import NmeInvoicingCommon


@tagged("post_install", "-at_install")
class TestNmeInvoicingSecurity(NmeInvoicingCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.salesman = new_test_user(
            cls.env, login="nme_inv_salesman", groups="nme_sales.nme_group_sales_user"
        )
        cls.salesman_2 = new_test_user(
            cls.env,
            login="nme_inv_salesman_2",
            groups="nme_sales.nme_group_sales_user",
        )
        cls.internal_user = new_test_user(
            cls.env, login="nme_inv_internal", groups="base.group_user"
        )

    def _invoiced_order_of(self, salesman):
        order = self._create_order([(self.service, 1)], user_id=salesman.id)
        order.action_confirm()
        order.action_create_invoice()
        return order

    def test_salesman_reads_invoices_of_own_orders_only(self):
        own = self._invoiced_order_of(self.salesman)
        other = self._invoiced_order_of(self.salesman_2)
        Invoice = self.env["nme.invoice"].with_user(self.salesman)
        visible = Invoice.search([("id", "in", (own | other).invoice_ids.ids)])
        self.assertEqual(visible, own.invoice_ids)
        self.assertEqual(
            own.invoice_ids.with_user(self.salesman).line_ids.product_id, self.service
        )

    @mute_logger("odoo.addons.base.models.ir_access")
    def test_internal_user_cannot_read_invoices(self):
        invoice = self._create_invoice()
        with self.assertRaises(AccessError):
            invoice.with_user(self.internal_user).read(["name"])
        with self.assertRaises(AccessError):
            self.env["nme.invoice.aging.report"].with_user(self.internal_user).search(
                []
            )
