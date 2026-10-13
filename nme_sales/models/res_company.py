from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    nme_quotation_validity_days = fields.Integer(
        string="Default Quotation Validity (Days)",
        default=30,
        help="Days after which a new quotation expires. 0 means no expiration.",
    )
