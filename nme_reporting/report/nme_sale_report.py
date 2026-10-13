from odoo import fields, models, tools
from odoo.tools import SQL


class NmeSaleReport(models.Model):
    """Sales analysis per confirmed order line, with the margin of the
    delivered goods (revenue of the delivered quantity minus the cost of the
    stock moves that delivered them, returns included)."""

    _name = "nme.sale.report"
    _description = "Sales Analysis"
    _auto = False
    _rec_name = "date"
    _order = "date desc"
    _depends = {
        "nme.sale.order": [
            "date_order",
            "partner_id",
            "user_id",
            "company_id",
            "currency_id",
            "warehouse_id",
            "state",
        ],
        "nme.sale.order.line": [
            "order_id",
            "product_id",
            "quantity",
            "qty_delivered",
            "qty_invoiced",
            "price_subtotal",
            "price_total",
        ],
        "nme.stock.move": ["sale_line_id", "state", "value", "location_dest_usage"],
        "nme.product": ["categ_id"],
    }

    order_id = fields.Many2one("nme.sale.order", readonly=True)
    date = fields.Datetime(string="Order Date", readonly=True)
    partner_id = fields.Many2one("res.partner", string="Customer", readonly=True)
    user_id = fields.Many2one("res.users", string="Salesperson", readonly=True)
    company_id = fields.Many2one("res.company", readonly=True)
    currency_id = fields.Many2one("res.currency", readonly=True)
    warehouse_id = fields.Many2one("nme.warehouse", readonly=True)
    product_id = fields.Many2one("nme.product", readonly=True)
    categ_id = fields.Many2one(
        "nme.product.category", string="Product Category", readonly=True
    )
    qty_ordered = fields.Float(digits="Nusantara Quantity", readonly=True)
    qty_delivered = fields.Float(digits="Nusantara Quantity", readonly=True)
    qty_invoiced = fields.Float(digits="Nusantara Quantity", readonly=True)
    amount_untaxed = fields.Monetary(string="Untaxed Total", readonly=True)
    amount_total = fields.Monetary(string="Total", readonly=True)
    amount_delivered = fields.Monetary(
        string="Delivered Revenue",
        readonly=True,
        help="Untaxed revenue of the delivered quantity.",
    )
    cost = fields.Monetary(
        string="Cost of Goods",
        readonly=True,
        help="Value of the delivery moves, at average cost.",
    )
    margin = fields.Monetary(readonly=True)

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute(
            SQL(
                """
                CREATE OR REPLACE VIEW %(table)s AS (
                    SELECT line.id AS id,
                           line.order_id,
                           sale.date_order AS date,
                           sale.partner_id,
                           sale.user_id,
                           sale.company_id,
                           sale.currency_id,
                           sale.warehouse_id,
                           line.product_id,
                           product.categ_id,
                           line.quantity AS qty_ordered,
                           line.qty_delivered,
                           line.qty_invoiced,
                           line.price_subtotal AS amount_untaxed,
                           line.price_total AS amount_total,
                           delivered.revenue AS amount_delivered,
                           COALESCE(moves.cost, 0) AS cost,
                           delivered.revenue - COALESCE(moves.cost, 0) AS margin
                      FROM nme_sale_order_line line
                      JOIN nme_sale_order sale ON sale.id = line.order_id
                      JOIN nme_product product ON product.id = line.product_id
                      LEFT JOIN (
                          SELECT move.sale_line_id,
                                 SUM(
                                     CASE WHEN move.location_dest_usage = 'customer'
                                          THEN move.value ELSE -move.value END
                                 ) AS cost
                            FROM nme_stock_move move
                           WHERE move.state = 'done'
                             AND move.sale_line_id IS NOT NULL
                           GROUP BY move.sale_line_id
                      ) AS moves ON moves.sale_line_id = line.id
                      CROSS JOIN LATERAL (
                          SELECT CASE WHEN line.quantity = 0 THEN 0
                                      ELSE line.price_subtotal * line.qty_delivered
                                           / line.quantity
                                 END AS revenue
                      ) AS delivered
                     WHERE sale.state = 'sale'
                )
                """,
                table=SQL.identifier(self._table),
            )
        )
