from odoo import fields, models, tools
from odoo.tools import SQL


class NmePurchaseReport(models.Model):
    """Purchase analysis per confirmed order line."""

    _name = "nme.purchase.report"
    _description = "Purchase Analysis"
    _auto = False
    _rec_name = "date"
    _order = "date desc"
    _depends = {
        "nme.purchase.order": [
            "date_order",
            "partner_id",
            "user_id",
            "company_id",
            "currency_id",
            "warehouse_id",
            "state",
        ],
        "nme.purchase.order.line": [
            "order_id",
            "product_id",
            "quantity",
            "qty_received",
            "qty_invoiced",
            "price_subtotal",
            "price_total",
        ],
        "nme.product": ["categ_id"],
    }

    order_id = fields.Many2one("nme.purchase.order", readonly=True)
    date = fields.Datetime(string="Order Date", readonly=True)
    partner_id = fields.Many2one("res.partner", string="Vendor", readonly=True)
    user_id = fields.Many2one("res.users", string="Buyer", readonly=True)
    company_id = fields.Many2one("res.company", readonly=True)
    currency_id = fields.Many2one("res.currency", readonly=True)
    warehouse_id = fields.Many2one("nme.warehouse", readonly=True)
    product_id = fields.Many2one("nme.product", readonly=True)
    categ_id = fields.Many2one(
        "nme.product.category", string="Product Category", readonly=True
    )
    qty_ordered = fields.Float(digits="Nusantara Quantity", readonly=True)
    qty_received = fields.Float(digits="Nusantara Quantity", readonly=True)
    qty_invoiced = fields.Float(
        string="Qty Billed", digits="Nusantara Quantity", readonly=True
    )
    amount_untaxed = fields.Monetary(string="Untaxed Total", readonly=True)
    amount_total = fields.Monetary(string="Total", readonly=True)
    price_average = fields.Monetary(
        string="Average Unit Price",
        aggregator="avg",
        readonly=True,
        help="Untaxed unit price after discount.",
    )

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute(
            SQL(
                """
                CREATE OR REPLACE VIEW %(table)s AS (
                    SELECT line.id AS id,
                           line.order_id,
                           po.date_order AS date,
                           po.partner_id,
                           po.user_id,
                           po.company_id,
                           po.currency_id,
                           po.warehouse_id,
                           line.product_id,
                           product.categ_id,
                           line.quantity AS qty_ordered,
                           line.qty_received,
                           line.qty_invoiced,
                           line.price_subtotal AS amount_untaxed,
                           line.price_total AS amount_total,
                           CASE WHEN line.quantity = 0 THEN 0
                                ELSE line.price_subtotal / line.quantity
                           END AS price_average
                      FROM nme_purchase_order_line line
                      JOIN nme_purchase_order po ON po.id = line.order_id
                      JOIN nme_product product ON product.id = line.product_id
                     WHERE po.state = 'purchase'
                )
                """,
                table=SQL.identifier(self._table),
            )
        )
