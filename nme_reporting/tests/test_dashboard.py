from datetime import timedelta

from odoo.tests import new_test_user, tagged

from odoo.addons.nme_invoicing.tests.common import NmeInvoicingCommon


@tagged("post_install", "-at_install")
class TestNmeDashboard(NmeInvoicingCommon):
    def _kpis(self, user=None):
        Dashboard = self.env["nme.dashboard"]
        if user:
            Dashboard = Dashboard.with_user(user)
        data = Dashboard.get_dashboard_data()
        return data, {kpi["key"]: kpi for kpi in data["kpis"]}

    def test_figures_for_a_manager(self):
        order = self._create_order([(self.product, 2)])  # 200,000 untaxed
        order.action_confirm()
        overdue = self._create_invoice(
            invoice_date=self._today() - timedelta(days=40),
            invoice_date_due=self._today() - timedelta(days=10),
        )
        overdue.action_post()
        self.product.min_qty = 500

        data, kpis = self._kpis()
        self.assertEqual(data["currency_id"], self.company.currency_id.id)
        self.assertGreaterEqual(kpis["sales_month"]["value"], 200000.0)
        self.assertGreaterEqual(kpis["orders_to_deliver"]["value"], 1)
        self.assertGreaterEqual(kpis["receivable"]["value"], 111000.0)
        self.assertTrue(kpis["overdue"]["alert"])
        self.assertTrue(kpis["low_stock"]["alert"])
        self.assertIn("po_to_approve", kpis)
        self.assertEqual(kpis["overdue"]["action"]["res_model"], "nme.invoice")

        chart = data["sales_chart"]
        self.assertEqual(len(chart), 6)
        self.assertGreaterEqual(chart[-1]["value"], 200000.0)

    def test_figures_follow_access_rights(self):
        salesman = new_test_user(
            self.env, login="nme_dash_salesman", groups="nme_sales.nme_group_sales_user"
        )
        data, kpis = self._kpis(salesman)
        self.assertIn("sales_month", kpis)
        self.assertNotIn("receivable", kpis)
        self.assertNotIn("low_stock", kpis)
        self.assertNotIn("po_to_approve", kpis)
        self.assertTrue(data["sales_chart"])

        internal = new_test_user(
            self.env, login="nme_dash_internal", groups="base.group_user"
        )
        data, kpis = self._kpis(internal)
        self.assertFalse(kpis)
        self.assertIsNone(data["sales_chart"])
