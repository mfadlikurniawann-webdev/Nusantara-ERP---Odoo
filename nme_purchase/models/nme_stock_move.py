from odoo import fields, models


class NmeStockMove(models.Model):
    _inherit = "nme.stock.move"

    purchase_line_id = fields.Many2one(
        "nme.purchase.order.line",
        string="Purchase Order Line",
        index="btree_not_null",
        copy=False,
    )
