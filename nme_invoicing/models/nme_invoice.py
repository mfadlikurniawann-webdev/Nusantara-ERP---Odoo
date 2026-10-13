from odoo import api, fields, models
from odoo.exceptions import UserError
from odoo.tools import float_compare, float_is_zero, format_amount

INVOICING_MANAGER_GROUP = "nme_invoicing.nme_group_invoicing_manager"


class NmeInvoice(models.Model):
    """Customer invoice or vendor bill.

    An invoice gets its number when it is posted, so posted invoices are
    numbered without gaps. The amount paid, the amount due and the payment
    state are computed from the posted payments.
    """

    _name = "nme.invoice"
    _description = "Invoice"
    _inherit = ["nme.trade.document.mixin"]
    _order = "invoice_date desc, id desc"

    _sequence_on_create = False
    _unlink_allowed_states = ("draft",)
    _state_transitions = {
        "draft": {"posted", "cancel"},
        "posted": {"draft", "cancel"},
        "cancel": {"draft"},
    }

    move_type = fields.Selection(
        [("out_invoice", "Customer Invoice"), ("in_invoice", "Vendor Bill")],
        string="Type",
        required=True,
        default="out_invoice",
        index=True,
    )
    state = fields.Selection(
        [("draft", "Draft"), ("posted", "Posted"), ("cancel", "Cancelled")],
        string="Status",
        required=True,
        readonly=True,
        copy=False,
        index=True,
        tracking=True,
        default="draft",
    )
    partner_id = fields.Many2one(required=True)
    payment_term_id = fields.Many2one(
        compute="_compute_payment_term_id", store=True, readonly=False, precompute=True
    )
    invoice_date = fields.Date(
        copy=False,
        index=True,
        tracking=True,
        help="Set to today when the invoice is posted without a date.",
    )
    invoice_date_due = fields.Date(
        string="Due Date",
        compute="_compute_invoice_date_due",
        store=True,
        readonly=False,
        copy=False,
        index=True,
        tracking=True,
    )
    ref = fields.Char(
        string="Partner Reference",
        copy=False,
        help="Vendor bill number, or order reference of the customer.",
    )
    sale_order_id = fields.Many2one(
        "nme.sale.order",
        string="Sales Order",
        readonly=True,
        copy=False,
        index="btree_not_null",
        check_company=True,
    )
    purchase_order_id = fields.Many2one(
        "nme.purchase.order",
        readonly=True,
        copy=False,
        index="btree_not_null",
        check_company=True,
    )
    line_ids = fields.One2many(
        "nme.invoice.line", "invoice_id", string="Invoice Lines", copy=True
    )
    payment_ids = fields.One2many("nme.payment", "invoice_id", string="Payments")
    payment_count = fields.Integer(compute="_compute_payment_count")
    amount_paid = fields.Monetary(compute="_compute_payment_state", store=True)
    amount_residual = fields.Monetary(
        string="Amount Due", compute="_compute_payment_state", store=True
    )
    payment_state = fields.Selection(
        [("not_paid", "Not Paid"), ("partial", "Partially Paid"), ("paid", "Paid")],
        compute="_compute_payment_state",
        store=True,
        copy=False,
        tracking=True,
    )
    is_overdue = fields.Boolean(
        string="Overdue",
        compute="_compute_is_overdue",
        store=True,
        help="Posted, not fully paid and past its due date. Refreshed every day.",
    )

    @api.depends("partner_id", "move_type", "company_id")
    def _compute_payment_term_id(self):
        for invoice in self:
            partner = invoice.partner_id.with_company(invoice.company_id)
            if invoice.move_type == "out_invoice":
                term = partner.nme_payment_term_id
            else:
                term = partner.nme_vendor_payment_term_id
            invoice.payment_term_id = term or invoice.company_id.nme_payment_term_id

    @api.depends("invoice_date", "payment_term_id")
    def _compute_invoice_date_due(self):
        for invoice in self:
            date = invoice.invoice_date or fields.Date.context_today(invoice)
            if invoice.payment_term_id:
                invoice.invoice_date_due = invoice.payment_term_id._get_due_date(date)
            else:
                invoice.invoice_date_due = date

    @api.depends("payment_ids")
    def _compute_payment_count(self):
        for invoice in self:
            invoice.payment_count = len(invoice.payment_ids)

    @api.depends("state", "amount_total", "payment_ids.amount", "payment_ids.state")
    def _compute_payment_state(self):
        for invoice in self:
            paid = sum(
                invoice.payment_ids.filtered(lambda p: p.state == "posted").mapped(
                    "amount"
                )
            )
            rounding = invoice.currency_id.rounding or 0.01
            invoice.amount_paid = paid
            invoice.amount_residual = invoice.amount_total - paid
            if invoice.state != "posted" or float_is_zero(
                paid, precision_rounding=rounding
            ):
                invoice.payment_state = "not_paid"
            elif (
                float_compare(paid, invoice.amount_total, precision_rounding=rounding)
                >= 0
            ):
                invoice.payment_state = "paid"
            else:
                invoice.payment_state = "partial"

    @api.depends("state", "payment_state", "invoice_date_due")
    def _compute_is_overdue(self):
        today = fields.Date.context_today(self)
        for invoice in self:
            invoice.is_overdue = bool(
                invoice.state == "posted"
                and invoice.payment_state != "paid"
                and invoice.invoice_date_due
                and invoice.invoice_date_due < today
            )

    @api.depends("name", "move_type", "state")
    def _compute_display_name(self):
        new_name = self.env._("New")
        for invoice in self:
            if invoice.name == new_name or not invoice.name:
                if invoice.move_type == "in_invoice":
                    invoice.display_name = self.env._("Draft Bill")
                else:
                    invoice.display_name = self.env._("Draft Invoice")
            else:
                invoice.display_name = invoice.name

    @api.ondelete(at_uninstall=False)
    def _unlink_except_numbered(self):
        new_name = self.env._("New")
        if any(invoice.name != new_name for invoice in self):
            raise UserError(
                self.env._(
                    "Numbered invoices cannot be deleted: cancel them to keep the "
                    "numbering without gaps."
                )
            )

    def _get_sequence_code(self, vals):
        if vals.get("move_type") == "in_invoice":
            return "nme.invoice.in"
        return "nme.invoice.out"

    def action_post(self):
        """Number the invoices and post them."""
        for invoice in self:
            if invoice.state != "draft":
                raise UserError(
                    self.env._("%s is not a draft invoice.", invoice.display_name)
                )
            if not invoice.line_ids:
                raise UserError(
                    self.env._("Add at least one line to %s.", invoice.display_name)
                )
        new_name = self.env._("New")
        for invoice in self:
            values = {}
            if not invoice.invoice_date:
                values["invoice_date"] = fields.Date.context_today(invoice)
            if invoice.name == new_name:
                values["name"] = invoice._next_sequence_number(
                    {
                        "move_type": invoice.move_type,
                        "company_id": invoice.company_id.id,
                    }
                )
            if values:
                invoice.write(values)
        self._set_state("posted")
        return True

    def action_draft(self):
        self._check_invoicing_manager(self.env._("reset invoices to draft"))
        self._check_no_posted_payment()
        self._set_state("draft")
        return True

    def action_cancel(self):
        if any(invoice.state == "posted" for invoice in self):
            self._check_invoicing_manager(self.env._("cancel posted invoices"))
        self._check_no_posted_payment()
        return super().action_cancel()

    def action_register_payment(self):
        self.ensure_one()
        if self.state != "posted":
            raise UserError(self.env._("Only posted invoices can be paid."))
        return {
            "name": self.env._("Register Payment"),
            "type": "ir.actions.act_window",
            "res_model": "nme.payment.register",
            "view_mode": "form",
            "views": [(False, "form")],
            "target": "new",
            "context": {"default_invoice_id": self.id},
        }

    def action_invoice_send(self):
        self.ensure_one()
        template = self.env.ref(
            "nme_invoicing.mail_template_nme_invoice", raise_if_not_found=False
        )
        return {
            "name": self.env._("Send Invoice"),
            "type": "ir.actions.act_window",
            "res_model": "mail.compose.message",
            "view_mode": "form",
            "views": [(False, "form")],
            "target": "new",
            "context": {
                "default_model": self._name,
                "default_res_ids": self.ids,
                "default_composition_mode": "comment",
                "default_template_id": template.id if template else False,
                "force_email": True,
            },
        }

    def action_view_payments(self):
        self.ensure_one()
        return {
            "name": self.env._("Payments"),
            "type": "ir.actions.act_window",
            "res_model": "nme.payment",
            "view_mode": "list,form",
            "domain": [("invoice_id", "=", self.id)],
            "context": {"create": False},
        }

    def _check_invoicing_manager(self, operation):
        if not self.env.user.has_group(INVOICING_MANAGER_GROUP):
            raise UserError(self.env._("Only invoicing managers can %s.", operation))

    def _check_no_posted_payment(self):
        if self.payment_ids.filtered(lambda p: p.state == "posted"):
            raise UserError(self.env._("Cancel the payments of the invoice first."))

    @api.model
    def _cron_update_overdue(self):
        """Refresh the overdue flag and warn the salesperson of new overdues."""
        today = fields.Date.context_today(self)
        candidates = self.search(
            [
                ("state", "=", "posted"),
                ("payment_state", "!=", "paid"),
                "|",
                ("is_overdue", "=", True),
                ("invoice_date_due", "<", today),
            ]
        )
        newly_overdue = candidates.filtered(lambda invoice: not invoice.is_overdue)
        candidates._compute_is_overdue()
        for invoice in newly_overdue.filtered(
            lambda inv: inv.is_overdue and inv.move_type == "out_invoice"
        ):
            invoice.activity_schedule(
                "nme_invoicing.mail_activity_type_overdue",
                user_id=invoice.user_id.id or self.env.user.id,
                note=self.env._(
                    "%(invoice)s is overdue since %(date)s: %(amount)s still due.",
                    invoice=invoice.name,
                    date=invoice.invoice_date_due,
                    amount=format_amount(
                        self.env, invoice.amount_residual, invoice.currency_id
                    ),
                ),
            )
