from datetime import timedelta

from odoo import api, fields, models
from odoo.exceptions import UserError
from odoo.fields import Command
from odoo.tools import float_compare, format_amount

SALES_MANAGER_GROUP = "nme_sales.nme_group_sales_manager"


class NmeSaleOrder(models.Model):
    """Quotation that becomes a sales order once confirmed.

    Confirming checks the customer's credit limit and creates the delivery of
    the goods; the delivered quantities come back from the stock ledger.
    """

    _name = "nme.sale.order"
    _description = "Sales Order"
    _inherit = ["nme.trade.document.mixin"]
    _order = "date_order desc, id desc"

    _state_transitions = {
        "draft": {"sent", "sale", "cancel"},
        "sent": {"sale", "cancel"},
        "sale": {"cancel"},
        "cancel": {"draft"},
    }

    def _default_validity_date(self):
        days = self.env.company.nme_quotation_validity_days
        if not days:
            return False
        return fields.Date.context_today(self) + timedelta(days=days)

    state = fields.Selection(
        [
            ("draft", "Quotation"),
            ("sent", "Quotation Sent"),
            ("sale", "Sales Order"),
            ("cancel", "Cancelled"),
        ],
        string="Status",
        required=True,
        readonly=True,
        copy=False,
        index=True,
        tracking=True,
        group_expand=True,
        default="draft",
    )
    partner_id = fields.Many2one(string="Customer", required=True)
    payment_term_id = fields.Many2one(
        compute="_compute_payment_term_id", store=True, readonly=False, precompute=True
    )
    date_order = fields.Datetime(
        string="Order Date",
        required=True,
        index=True,
        copy=False,
        default=fields.Datetime.now,
        help="Quotation date, replaced by the confirmation date.",
    )
    validity_date = fields.Date(
        string="Expiration",
        copy=False,
        default=lambda self: self._default_validity_date(),
    )
    commitment_date = fields.Datetime(
        string="Delivery Date",
        copy=False,
        help="Delivery date promised to the customer.",
    )
    warehouse_id = fields.Many2one(
        "nme.warehouse",
        required=True,
        check_company=True,
        default=lambda self: self.env["nme.picking"]._default_warehouse_id(),
    )
    line_ids = fields.One2many(
        "nme.sale.order.line", "order_id", string="Order Lines", copy=True
    )
    picking_ids = fields.One2many("nme.picking", "sale_id", string="Deliveries")
    delivery_count = fields.Integer(compute="_compute_delivery_count")
    delivery_status = fields.Selection(
        [
            ("nothing", "Nothing to Deliver"),
            ("to_deliver", "To Deliver"),
            ("partial", "Partially Delivered"),
            ("delivered", "Delivered"),
        ],
        compute="_compute_delivery_status",
        store=True,
    )
    credit_warning = fields.Char(compute="_compute_credit_warning")

    @api.depends("partner_id", "company_id")
    def _compute_payment_term_id(self):
        for order in self:
            partner = order.partner_id.with_company(order.company_id)
            order.payment_term_id = (
                partner.nme_payment_term_id or order.company_id.nme_payment_term_id
            )

    @api.depends("picking_ids")
    def _compute_delivery_count(self):
        for order in self:
            order.delivery_count = len(order.picking_ids)

    @api.depends(
        "state", "line_ids.qty_delivered", "line_ids.quantity", "line_ids.product_id"
    )
    def _compute_delivery_status(self):
        precision = self.env["decimal.precision"].precision_get("Nusantara Quantity")
        for order in self:
            goods = order.line_ids.filtered(
                lambda line: line.product_id.type == "goods"
            )
            if order.state != "sale" or not goods:
                order.delivery_status = "nothing"
            elif all(
                float_compare(
                    line.qty_delivered, line.quantity, precision_digits=precision
                )
                >= 0
                for line in goods
            ):
                order.delivery_status = "delivered"
            elif any(line.qty_delivered > 0 for line in goods):
                order.delivery_status = "partial"
            else:
                order.delivery_status = "to_deliver"

    @api.depends("partner_id", "company_id", "amount_total", "state")
    def _compute_credit_warning(self):
        for order in self:
            if order.state in ("draft", "sent") and order.partner_id:
                order.credit_warning = order._get_credit_message()
            else:
                order.credit_warning = False

    def message_post(self, **kwargs):
        # Set by action_quotation_send: emailing a quotation marks it as sent.
        if self.env.context.get("nme_mark_quotation_sent"):
            self.filtered(lambda order: order.state == "draft")._set_state("sent")
        return super().message_post(**kwargs)

    def action_quotation_send(self):
        """Open the email composer with the quotation template and PDF."""
        self.ensure_one()
        template = self.env.ref(
            "nme_sales.mail_template_nme_sale_order", raise_if_not_found=False
        )
        return {
            "name": self.env._("Send Quotation"),
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
                "nme_mark_quotation_sent": True,
            },
        }

    def action_confirm(self):
        """Confirm the quotations: credit check, then delivery of the goods."""
        for order in self:
            if not order.line_ids:
                raise UserError(
                    self.env._("Add at least one line to %s.", order.display_name)
                )
        self._check_credit_limit()
        self._set_state("sale")
        self.date_order = fields.Datetime.now()
        self._create_deliveries()
        return True

    def action_cancel(self):
        for order in self:
            if any(line.qty_delivered for line in order.line_ids):
                raise UserError(
                    self.env._(
                        "Goods of %s were delivered: return them before cancelling "
                        "the order.",
                        order.display_name,
                    )
                )
        res = super().action_cancel()
        self.picking_ids.filtered(lambda p: p.state == "draft").action_cancel()
        return res

    def action_draft(self):
        self._set_state("draft")
        return True

    def action_view_deliveries(self):
        self.ensure_one()
        action = {
            "name": self.env._("Deliveries"),
            "type": "ir.actions.act_window",
            "res_model": "nme.picking",
            "view_mode": "list,form",
            "domain": [("sale_id", "=", self.id)],
            "context": {"default_sale_id": self.id, "create": False},
        }
        if len(self.picking_ids) == 1:
            action.update(
                view_mode="form", views=[(False, "form")], res_id=self.picking_ids.id
            )
        return action

    def _get_credit_message(self):
        """Explain why confirming would exceed the credit limit, or return False."""
        self.ensure_one()
        partner = self.partner_id.commercial_partner_id.with_company(self.company_id)
        limit = partner.nme_credit_limit
        if partner.nme_credit_policy in (False, "none") or not limit:
            return False
        exposure = partner._get_credit_exposure() + self.amount_total
        currency = self.currency_id
        if float_compare(exposure, limit, precision_rounding=currency.rounding) <= 0:
            return False
        return self.env._(
            "%(partner)s would owe %(exposure)s, above the credit limit of %(limit)s.",
            partner=partner.display_name,
            exposure=format_amount(self.env, exposure, currency),
            limit=format_amount(self.env, limit, currency),
        )

    def _check_credit_limit(self):
        is_manager = self.env.user.has_group(SALES_MANAGER_GROUP)
        for order in self:
            message = order._get_credit_message()
            if not message:
                continue
            policy = order.partner_id.commercial_partner_id.with_company(
                order.company_id
            ).nme_credit_policy
            if policy == "block" and not is_manager:
                raise UserError(
                    self.env._(
                        "%s Only a sales manager can confirm this order.", message
                    )
                )
            # Keep a trace of the warning or of the manager's override.
            order.message_post(body=message)

    def _create_deliveries(self):
        values = []
        for order in self:
            lines = order.line_ids.filtered(
                lambda line: line.product_id.type == "goods"
            )
            if lines:
                values.append(order._prepare_delivery_values(lines))
        return self.env["nme.picking"].create(values)

    def _prepare_delivery_values(self, lines):
        self.ensure_one()
        return {
            "picking_type": "outgoing",
            "partner_id": self.partner_id.id,
            "warehouse_id": self.warehouse_id.id,
            "company_id": self.company_id.id,
            "origin": self.name,
            "sale_id": self.id,
            "scheduled_date": self.commitment_date or fields.Datetime.now(),
            "move_ids": [
                Command.create(
                    {
                        "product_id": line.product_id.id,
                        "quantity": line.quantity,
                        "name": line.name,
                        "sale_line_id": line.id,
                    }
                )
                for line in lines
            ],
        }
