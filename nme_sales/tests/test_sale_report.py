from odoo.tests import tagged

from .common import NmeSalesCommon


@tagged("post_install", "-at_install")
class TestNmeSaleReport(NmeSalesCommon):
    def test_quotation_report_renders(self):
        order = self._create_order()
        html, report_format = self.env["ir.actions.report"]._render_qweb_html(
            "nme_sales.report_nme_sale_order", order.ids
        )
        self.assertEqual(report_format, "html")
        content = html.decode()
        self.assertIn(order.name, content)
        self.assertIn("Quotation", content)
        self.assertIn("Test Rice", content)

    def test_delivery_slip_renders(self):
        order = self._create_order()
        order.action_confirm()
        html, _format = self.env["ir.actions.report"]._render_qweb_html(
            "nme_inventory.report_nme_picking", order.picking_ids.ids
        )
        self.assertIn(order.picking_ids.name, html.decode())
        self.assertIn("Delivery Slip", html.decode())

    def test_mail_template_renders_subject(self):
        order = self._create_order()
        template = self.env.ref("nme_sales.mail_template_nme_sale_order")
        subject = template._render_field("subject", order.ids)[order.id]
        self.assertIn(order.name, subject)
        self.assertIn("Quotation", subject)
