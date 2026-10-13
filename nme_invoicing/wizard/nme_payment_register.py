from odoo import api, fields, models
from odoo.exceptions import UserError
from odoo.tools import float_compare


class NmePaymentRegister(models.TransientModel):
    """Register a full or partial payment of a posted invoice."""

    _name = "nme.payment.register"
    _description = "Register Payment"

    invoice_id = fields.Many2one(
        "nme.invoice",
        required=True,
        domain=[("state", "=", "posted")],
        default=lambda self: self.env.context.get("active_id"),
    )
    company_id = fields.Many2one(related="invoice_id.company_id")
    currency_id = fields.Many2one(related="invoice_id.currency_id")
    amount_residual = fields.Monetary(related="invoice_id.amount_residual")
    amount = fields.Monetary(
        compute="_compute_amount", store=True, readonly=False, required=True
    )
    date = fields.Date(required=True, default=fields.Date.context_today)
    method = fields.Selection(
        [("bank", "Bank Transfer"), ("cash", "Cash"), ("other", "Other")],
        string="Payment Method",
        required=True,
        default="bank",
    )
    memo = fields.Char(compute="_compute_memo", store=True, readonly=False)

    @api.depends("invoice_id")
    def _compute_amount(self):
        for wizard in self:
            wizard.amount = wizard.invoice_id.amount_residual

    @api.depends("invoice_id")
    def _compute_memo(self):
        for wizard in self:
            wizard.memo = wizard.invoice_id.name

    def action_create_payment(self):
        self.ensure_one()
        invoice = self.invoice_id
        if invoice.state != "posted":
            raise UserError(self.env._("Only posted invoices can be paid."))
        rounding = self.currency_id.rounding or 0.01
        if float_compare(self.amount, 0.0, precision_rounding=rounding) <= 0:
            raise UserError(self.env._("The amount must be positive."))
        if (
            float_compare(
                self.amount, invoice.amount_residual, precision_rounding=rounding
            )
            > 0
        ):
            raise UserError(
                self.env._(
                    "%s cannot be paid more than its amount due.", invoice.display_name
                )
            )
        self.env["nme.payment"].create(
            {
                "invoice_id": invoice.id,
                "company_id": invoice.company_id.id,
                "amount": self.amount,
                "date": self.date,
                "method": self.method,
                "memo": self.memo,
            }
        )
        return {"type": "ir.actions.act_window_close"}
