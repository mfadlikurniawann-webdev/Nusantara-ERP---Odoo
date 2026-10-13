from odoo import fields, models


class NmeStockAdjustmentReason(models.Model):
    """Why the counted stock differs from the system (damaged, lost, count...)."""

    _name = "nme.stock.adjustment.reason"
    _description = "Stock Adjustment Reason"
    _order = "sequence, id"

    name = fields.Char(required=True, translate=True)
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)
