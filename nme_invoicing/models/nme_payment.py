from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.tools import float_compare

INVOICING_MANAGER_GROUP = "nme_invoicing.nme_group_invoicing_manager"


class NmePayment(models.Model):
    """Payment received from a customer or sent to a vendor for one invoice.

    An invoice can have several payments (partial payments) but can never be
    paid more than its total. Payments are never deleted, only cancelled.
    """

    _name = "nme.payment"
    _description = "Payment"
    _inherit = ["nme.document.mixin"]
    _order = "date desc, id desc"

    _unlink_allowed_states = ()
    _state_transitions = {"posted": {"cancel"}}

    state = fields.Selection(
        [("posted", "Posted"), ("cancel", "Cancelled")],
        string="Status",
        required=True,
        readonly=True,
        copy=False,
        index=True,
        tracking=True,
        default="posted",
    )
    invoice_id = fields.Many2one(
        "nme.invoice",
        required=True,
        index=True,
        ondelete="restrict",
        check_company=True,
    )
    partner_id = fields.Many2one(
        related="invoice_id.partner_id", store=True, index=True
    )
    payment_type = fields.Selection(
        [("inbound", "Receive Money"), ("outbound", "Send Money")],
        compute="_compute_payment_type",
        store=True,
    )
    currency_id = fields.Many2one(related="company_id.currency_id")
    amount = fields.Monetary(required=True, tracking=True)
    date = fields.Date(
        required=True, index=True, default=fields.Date.context_today, tracking=True
    )
    method = fields.Selection(
        [("bank", "Bank Transfer"), ("cash", "Cash"), ("other", "Other")],
        string="Payment Method",
        required=True,
        default="bank",
    )
    memo = fields.Char()

    _amount_positive = models.Constraint(
        "CHECK(amount > 0)", "The amount of a payment must be positive."
    )

    @api.depends("invoice_id.move_type")
    def _compute_payment_type(self):
        for payment in self:
            if payment.invoice_id.move_type == "in_invoice":
                payment.payment_type = "outbound"
            else:
                payment.payment_type = "inbound"

    @api.constrains("amount", "state", "invoice_id")
    def _check_invoice_not_overpaid(self):
        for invoice in self.invoice_id:
            if invoice.state != "posted" and invoice.payment_ids.filtered(
                lambda p: p.state == "posted"
            ):
                raise ValidationError(self.env._("Only posted invoices can be paid."))
            rounding = invoice.currency_id.rounding or 0.01
            if (
                float_compare(
                    invoice.amount_paid,
                    invoice.amount_total,
                    precision_rounding=rounding,
                )
                > 0
            ):
                raise ValidationError(
                    self.env._(
                        "%s would be paid more than its total.", invoice.display_name
                    )
                )

    def action_cancel(self):
        if not self.env.user.has_group(INVOICING_MANAGER_GROUP):
            raise UserError(self.env._("Only invoicing managers can cancel payments."))
        return super().action_cancel()
