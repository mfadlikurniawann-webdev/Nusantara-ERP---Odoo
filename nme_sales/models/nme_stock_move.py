from odoo import fields, models


class NmeStockMove(models.Model):
    _inherit = "nme.stock.move"

    sale_line_id = fields.Many2one(
        "nme.sale.order.line",
        string="Sales Order Line",
        index="btree_not_null",
        copy=False,
    )
