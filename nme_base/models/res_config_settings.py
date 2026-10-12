from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    nme_sale_tax_id = fields.Many2one(
        related="company_id.nme_sale_tax_id", readonly=False
    )
    nme_purchase_tax_id = fields.Many2one(
        related="company_id.nme_purchase_tax_id", readonly=False
    )
    nme_payment_term_id = fields.Many2one(
        related="company_id.nme_payment_term_id", readonly=False
    )
