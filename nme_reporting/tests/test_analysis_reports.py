from odoo.tests import tagged

from odoo.addons.nme_invoicing.tests.common import NmeInvoicingCommon


@tagged("post_install", "-at_install")
class TestNmeAnalysisReports(NmeInvoicingCommon):
    def test_sales_report_margin_on_delivered_goods(self):
        # 100 units in stock at 80,000 (see NmeSalesCommon).
        order = self._create_order([(self.product, 4)])  # 4 x 100,000
        order.action_confirm()
        delivery = order.picking_ids
        delivery.action_validate()
        line = self.env["nme.sale.report"].search([("order_id", "=", order.id)])
        self.assertEqual(line.qty_ordered, 4)
        self.assertEqual(line.qty_delivered, 4)
        self.assertEqual(line.amount_untaxed, 400000.0)
        self.assertEqual(line.cost, 320000.0)
        self.assertEqual(line.margin, 80000.0)
        self.assertEqual(line.categ_id, self.categ)

        # A returned unit leaves the margin of the units actually sold.
        returned = self.env["nme.picking"].browse(
            delivery.action_create_return()["res_id"]
        )
        returned.move_ids.quantity = 1
        returned.action_validate()
        # Report rows are cached like records: read the view again.
        self.env["nme.sale.report"].invalidate_model()
        line = self.env["nme.sale.report"].search([("order_id", "=", order.id)])
        self.assertEqual(line.qty_delivered, 3)
        self.assertEqual(line.amount_delivered, 300000.0)
        self.assertEqual(line.cost, 240000.0)
        self.assertEqual(line.margin, 60000.0)

    def test_quotations_are_not_in_the_sales_report(self):
        order = self._create_order()
        self.assertFalse(
            self.env["nme.sale.report"].search([("order_id", "=", order.id)])
        )

    def test_purchase_report_average_price(self):
        po = self._create_po([(self.product, 10, 90000.0)])
        po.line_ids.discount = 10
        po.action_confirm()
        line = self.env["nme.purchase.report"].search([("order_id", "=", po.id)])
        self.assertEqual(line.qty_ordered, 10)
        self.assertEqual(line.amount_untaxed, 810000.0)
        self.assertEqual(line.price_average, 81000.0)
        self.assertEqual(line.partner_id, self.vendor)

    def test_stock_report_per_warehouse(self):
        transfer = self._create_picking(
            "internal", [(self.product, 30)], warehouse_dest_id=self.warehouse_2.id
        )
        transfer.action_validate()
        rows = self.env["nme.stock.report"].search(
            [("product_id", "=", self.product.id)]
        )
        by_warehouse = {row.warehouse_id: row for row in rows}
        self.assertEqual(by_warehouse[self.warehouse].quantity, 70)
        self.assertEqual(by_warehouse[self.warehouse_2].quantity, 30)
        self.assertEqual(by_warehouse[self.warehouse].avg_cost, 80000.0)
        self.assertEqual(by_warehouse[self.warehouse_2].value, 30 * 80000.0)
