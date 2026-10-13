from odoo import fields, models, tools
from odoo.tools import SQL


class NmeStockReport(models.Model):
    """Quantity and value of each product per internal location.

    Quantities are summed from the done stock moves (in minus out); the value
    uses the average cost of the product in the company of the location,
    stored by the ORM as a JSON object keyed by company id.
    """

    _name = "nme.stock.report"
    _description = "Stock by Warehouse"
    _auto = False
    _order = "warehouse_id, product_id"
    _depends = {
        "nme.stock.move": [
            "product_id",
            "quantity",
            "location_id",
            "location_dest_id",
            "state",
        ],
        "nme.location": ["usage", "warehouse_id", "company_id"],
        "nme.product": ["avg_cost", "categ_id", "uom_id"],
    }

    product_id = fields.Many2one("nme.product", readonly=True)
    categ_id = fields.Many2one(
        "nme.product.category", string="Product Category", readonly=True
    )
    uom_id = fields.Many2one("nme.uom", string="Unit", readonly=True)
    warehouse_id = fields.Many2one("nme.warehouse", readonly=True)
    location_id = fields.Many2one("nme.location", readonly=True)
    company_id = fields.Many2one("res.company", readonly=True)
    currency_id = fields.Many2one("res.currency", readonly=True)
    quantity = fields.Float(digits="Nusantara Quantity", readonly=True)
    avg_cost = fields.Float(
        string="Average Cost", digits=(16, 2), aggregator="avg", readonly=True
    )
    value = fields.Monetary(readonly=True)

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute(
            SQL(
                """
                CREATE OR REPLACE VIEW %(table)s AS (
                    SELECT ROW_NUMBER() OVER (
                               ORDER BY flows.location_id, flows.product_id
                           ) AS id,
                           flows.product_id,
                           product.categ_id,
                           product.uom_id,
                           location.warehouse_id,
                           flows.location_id,
                           location.company_id,
                           company.currency_id,
                           SUM(flows.quantity) AS quantity,
                           costs.avg_cost,
                           SUM(flows.quantity) * costs.avg_cost AS value
                      FROM (
                          SELECT location_dest_id AS location_id,
                                 product_id,
                                 quantity
                            FROM nme_stock_move
                           WHERE state = 'done'
                          UNION ALL
                          SELECT location_id, product_id, -quantity
                            FROM nme_stock_move
                           WHERE state = 'done'
                      ) AS flows
                      JOIN nme_location location
                        ON location.id = flows.location_id
                       AND location.usage = 'internal'
                      JOIN res_company company ON company.id = location.company_id
                      JOIN nme_product product ON product.id = flows.product_id
                      CROSS JOIN LATERAL (
                          SELECT COALESCE(
                                     (product.avg_cost ->> location.company_id::text)
                                         ::numeric,
                                     0
                                 ) AS avg_cost
                      ) AS costs
                     GROUP BY flows.location_id, flows.product_id, product.categ_id,
                              product.uom_id, location.warehouse_id,
                              location.company_id, company.currency_id,
                              costs.avg_cost
                    HAVING SUM(flows.quantity) != 0
                )
                """,
                table=SQL.identifier(self._table),
            )
        )
