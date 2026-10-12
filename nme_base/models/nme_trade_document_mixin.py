from odoo import api, fields, models


class NmeTradeDocumentMixin(models.AbstractModel):
    """Document with a partner, priced lines and totals (orders and invoices).

    The concrete model must define ``line_ids`` as a One2many towards a model
    inheriting ``nme.trade.line.mixin``.
    """

    _name = "nme.trade.document.mixin"
    _description = "Nusantara ERP Trade Document"
    _inherit = ["nme.document.mixin"]

    partner_id = fields.Many2one(
        "res.partner", index=True, tracking=True, check_company=True
    )
    currency_id = fields.Many2one(
        "res.currency", related="company_id.currency_id", store=True
    )
    payment_term_id = fields.Many2one(
        "nme.payment.term", string="Payment Terms", check_company=True, tracking=True
    )
    amount_untaxed = fields.Monetary(
        string="Untaxed Amount", compute="_compute_amounts", store=True
    )
    amount_tax = fields.Monetary(string="Taxes", compute="_compute_amounts", store=True)
    amount_total = fields.Monetary(
        string="Total", compute="_compute_amounts", store=True, tracking=True
    )

    @api.depends("line_ids.price_subtotal", "line_ids.price_tax")
    def _compute_amounts(self):
        for document in self:
            lines = document.line_ids
            document.amount_untaxed = sum(lines.mapped("price_subtotal"))
            document.amount_tax = sum(lines.mapped("price_tax"))
            document.amount_total = document.amount_untaxed + document.amount_tax
