from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    nme_sale_tax_id = fields.Many2one(
        "nme.tax",
        string="Default Sales Tax",
        domain="[('type_tax_use', '=', 'sale'), ('company_id', '=', id)]",
    )
    nme_purchase_tax_id = fields.Many2one(
        "nme.tax",
        string="Default Purchase Tax",
        domain="[('type_tax_use', '=', 'purchase'), ('company_id', '=', id)]",
    )
    nme_payment_term_id = fields.Many2one(
        "nme.payment.term",
        string="Default Payment Terms",
        domain="[('company_id', 'in', [id, False])]",
    )
