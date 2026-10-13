from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    nme_company_currency_id = fields.Many2one(related="company_id.currency_id")
    nme_po_approval_amount = fields.Monetary(
        related="company_id.nme_po_approval_amount",
        currency_field="nme_company_currency_id",
        readonly=False,
    )
