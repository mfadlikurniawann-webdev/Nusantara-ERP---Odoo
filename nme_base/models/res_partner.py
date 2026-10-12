from odoo import fields, models


class ResPartner(models.Model):
    """Customer/vendor flags and per-company payment terms.

    The NPWP (Indonesian tax number) is the standard ``vat`` field: Odoo
    already validates its format for Indonesian partners, so no custom check
    is needed here.
    """

    _inherit = "res.partner"

    nme_is_customer = fields.Boolean(string="Is a Customer")
    nme_is_vendor = fields.Boolean(string="Is a Vendor")
    nme_payment_term_id = fields.Many2one(
        "nme.payment.term",
        string="Customer Payment Terms",
        company_dependent=True,
        help="Payment terms proposed on sales orders and customer invoices.",
    )
    nme_vendor_payment_term_id = fields.Many2one(
        "nme.payment.term",
        string="Vendor Payment Terms",
        company_dependent=True,
        help="Payment terms proposed on purchase orders and vendor bills.",
    )
