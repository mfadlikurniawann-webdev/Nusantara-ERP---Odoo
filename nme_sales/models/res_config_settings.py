from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    nme_quotation_validity_days = fields.Integer(
        related="company_id.nme_quotation_validity_days", readonly=False
    )
