from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    nme_po_approval_amount = fields.Monetary(
        string="Purchase Approval Amount",
        currency_field="currency_id",
        default=50000000.0,
        help="Purchase orders reaching this total (taxes included) must be "
        "approved by a purchase manager. 0 disables the approval.",
    )
