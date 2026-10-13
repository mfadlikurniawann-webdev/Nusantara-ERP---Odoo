from odoo import api, fields, models
from odoo.exceptions import UserError
from odoo.fields import Command
from odoo.tools import float_compare, format_amount

PURCHASE_MANAGER_GROUP = "nme_purchase.nme_group_purchase_manager"


class NmePurchaseOrder(models.Model):
    """Request for quotation that becomes a purchase order once confirmed.

    Orders whose total reaches the company approval threshold must be
    approved by a purchase manager before they are confirmed. Confirmed
    orders create the receipt of the goods; receiving them updates the
    average cost with the net purchase price.
    """

    _name = "nme.purchase.order"
    _description = "Purchase Order"
    _inherit = ["nme.trade.document.mixin"]
    _order = "date_order desc, id desc"

    _state_transitions = {
        "draft": {"sent", "to_approve", "purchase", "cancel"},
        "sent": {"to_approve", "purchase", "cancel"},
        "to_approve": {"purchase", "draft", "cancel"},
        "purchase": {"cancel"},
        "cancel": {"draft"},
    }

    state = fields.Selection(
        [
            ("draft", "RFQ"),
            ("sent", "RFQ Sent"),
            ("to_approve", "To Approve"),
            ("purchase", "Purchase Order"),
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
    partner_id = fields.Many2one(string="Vendor", required=True)
    partner_ref = fields.Char(
        string="Vendor Reference", copy=False, help="Reference of the vendor's quote."
    )
    payment_term_id = fields.Many2one(
        compute="_compute_payment_term_id", store=True, readonly=False, precompute=True
    )
    date_order = fields.Datetime(
        string="Order Date",
        required=True,
        index=True,
        copy=False,
        default=fields.Datetime.now,
        help="RFQ date, replaced by the confirmation date.",
    )
    date_planned = fields.Datetime(
        string="Expected Arrival", help="Date the vendor promised to deliver."
    )
    warehouse_id = fields.Many2one(
        "nme.warehouse",
        string="Deliver To",
        required=True,
        check_company=True,
        default=lambda self: self.env["nme.picking"]._default_warehouse_id(),
    )
    line_ids = fields.One2many(
        "nme.purchase.order.line", "order_id", string="Order Lines", copy=True
    )
    picking_ids = fields.One2many("nme.picking", "purchase_id", string="Receipts")
    receipt_count = fields.Integer(compute="_compute_receipt_count")
    receipt_status = fields.Selection(
        [
            ("nothing", "Nothing to Receive"),
            ("to_receive", "To Receive"),
            ("partial", "Partially Received"),
            ("received", "Received"),
        ],
        compute="_compute_receipt_status",
        store=True,
    )
    approval_required = fields.Boolean(compute="_compute_approval_required")
    approved_by_id = fields.Many2one("res.users", readonly=True, copy=False)
    approval_date = fields.Datetime(string="Approved On", readonly=True, copy=False)

    @api.depends("partner_id", "company_id")
    def _compute_payment_term_id(self):
        for order in self:
            partner = order.partner_id.with_company(order.company_id)
            order.payment_term_id = (
                partner.nme_vendor_payment_term_id
                or order.company_id.nme_payment_term_id
            )

    @api.depends("picking_ids")
    def _compute_receipt_count(self):
        for order in self:
            order.receipt_count = len(order.picking_ids)

    @api.depends(
        "state", "line_ids.qty_received", "line_ids.quantity", "line_ids.product_id"
    )
    def _compute_receipt_status(self):
        precision = self.env["decimal.precision"].precision_get("Nusantara Quantity")
        for order in self:
            goods = order.line_ids.filtered(
                lambda line: line.product_id.type == "goods"
            )
            if order.state != "purchase" or not goods:
                order.receipt_status = "nothing"
            elif all(
                float_compare(
                    line.qty_received, line.quantity, precision_digits=precision
                )
                >= 0
                for line in goods
            ):
                order.receipt_status = "received"
            elif any(line.qty_received > 0 for line in goods):
                order.receipt_status = "partial"
            else:
                order.receipt_status = "to_receive"

    @api.depends("amount_total", "company_id.nme_po_approval_amount")
    def _compute_approval_required(self):
        for order in self:
            threshold = order.company_id.nme_po_approval_amount
            order.approval_required = bool(threshold) and (
                float_compare(
                    order.amount_total,
                    threshold,
                    precision_rounding=order.currency_id.rounding or 0.01,
                )
                >= 0
            )

    def message_post(self, **kwargs):
        # Set by action_rfq_send: emailing an RFQ marks it as sent.
        if self.env.context.get("nme_mark_rfq_sent"):
            self.filtered(lambda order: order.state == "draft")._set_state("sent")
        return super().message_post(**kwargs)

    def action_rfq_send(self):
        """Open the email composer with the RFQ / purchase order template."""
        self.ensure_one()
        template = self.env.ref(
            "nme_purchase.mail_template_nme_purchase_order", raise_if_not_found=False
        )
        return {
            "name": self.env._("Send by Email"),
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
                "nme_mark_rfq_sent": True,
            },
        }

    def action_confirm(self):
        """Confirm the RFQs, or send them for approval above the threshold."""
        for order in self:
            if not order.line_ids:
                raise UserError(
                    self.env._("Add at least one line to %s.", order.display_name)
                )
        is_manager = self.env.user.has_group(PURCHASE_MANAGER_GROUP)
        to_approve = self.filtered(lambda o: o.approval_required and not is_manager)
        to_approve._request_approval()
        (self - to_approve)._approve()
        return True

    def action_approve(self):
        if not self.env.user.has_group(PURCHASE_MANAGER_GROUP):
            raise UserError(self.env._("Only purchase managers can approve orders."))
        if any(order.state != "to_approve" for order in self):
            raise UserError(
                self.env._("Only orders waiting for approval can be approved.")
            )
        self._approve()
        return True

    def action_reject(self):
        if not self.env.user.has_group(PURCHASE_MANAGER_GROUP):
            raise UserError(self.env._("Only purchase managers can reject orders."))
        self._set_state("draft")
        self._close_approval_activities()
        for order in self:
            order.message_post(body=self.env._("Rejected by %s.", self.env.user.name))
        return True

    def action_cancel(self):
        for order in self:
            if any(line.qty_received for line in order.line_ids):
                raise UserError(
                    self.env._(
                        "Goods of %s were received: return them before cancelling "
                        "the order.",
                        order.display_name,
                    )
                )
        res = super().action_cancel()
        self.picking_ids.filtered(lambda p: p.state == "draft").action_cancel()
        self._close_approval_activities()
        return res

    def action_draft(self):
        self._set_state("draft")
        return True

    def action_view_receipts(self):
        self.ensure_one()
        action = {
            "name": self.env._("Receipts"),
            "type": "ir.actions.act_window",
            "res_model": "nme.picking",
            "view_mode": "list,form",
            "domain": [("purchase_id", "=", self.id)],
            "context": {"create": False},
        }
        if len(self.picking_ids) == 1:
            action.update(
                view_mode="form", views=[(False, "form")], res_id=self.picking_ids.id
            )
        return action

    def _request_approval(self):
        """Wait for a manager, who gets an activity on the order."""
        if not self:
            return
        self._set_state("to_approve")
        # Reading the group members is only used to pick the approvers.
        managers = (
            self.env.ref(PURCHASE_MANAGER_GROUP)
            .sudo()
            .user_ids.filtered(lambda user: user.active and not user.share)
        )
        for order in self:
            order_managers = managers.filtered(
                lambda user, o=order: o.company_id in user.company_ids
            )
            for manager in order_managers:
                order.activity_schedule(
                    "nme_purchase.mail_activity_type_po_approval",
                    user_id=manager.id,
                    note=self.env._(
                        "%(order)s amounts to %(amount)s and needs your approval.",
                        order=order.name,
                        amount=format_amount(
                            self.env, order.amount_total, order.currency_id
                        ),
                    ),
                )

    def _approve(self):
        """Confirm the orders and create the receipts of their goods."""
        if not self:
            return
        self._set_state("purchase")
        self.write(
            {
                "date_order": fields.Datetime.now(),
                "approved_by_id": self.env.user.id,
                "approval_date": fields.Datetime.now(),
            }
        )
        self._close_approval_activities()
        self._create_receipts()

    def _close_approval_activities(self):
        self.activity_unlink(["nme_purchase.mail_activity_type_po_approval"])

    def _create_receipts(self):
        values = []
        for order in self:
            lines = order.line_ids.filtered(
                lambda line: line.product_id.type == "goods"
            )
            if lines:
                values.append(order._prepare_receipt_values(lines))
        return self.env["nme.picking"].create(values)

    def _prepare_receipt_values(self, lines):
        self.ensure_one()
        return {
            "picking_type": "incoming",
            "partner_id": self.partner_id.id,
            "warehouse_id": self.warehouse_id.id,
            "company_id": self.company_id.id,
            "origin": self.name,
            "purchase_id": self.id,
            "scheduled_date": self.date_planned or fields.Datetime.now(),
            "move_ids": [
                Command.create(
                    {
                        "product_id": line.product_id.id,
                        "quantity": line.quantity,
                        "name": line.name,
                        "purchase_line_id": line.id,
                        "price_unit": line._get_net_unit_price(),
                    }
                )
                for line in lines
            ],
        }
