from odoo import api, fields, models
from odoo.exceptions import UserError
from odoo.fields import Command


class NmePurchaseOrder(models.Model):
    """Vendor bills of purchase orders: goods are billed on the received
    quantity, services on the ordered quantity."""

    _inherit = "nme.purchase.order"

    invoice_ids = fields.One2many(
        "nme.invoice", "purchase_order_id", string="Vendor Bills"
    )
    invoice_count = fields.Integer(compute="_compute_invoice_count")
    invoice_status = fields.Selection(
        [
            ("nothing", "Nothing to Bill"),
            ("to_invoice", "To Bill"),
            ("invoiced", "Fully Billed"),
        ],
        string="Billing Status",
        compute="_compute_invoice_status",
        store=True,
    )

    @api.depends("invoice_ids")
    def _compute_invoice_count(self):
        for order in self:
            order.invoice_count = len(order.invoice_ids)

    @api.depends(
        "state", "line_ids.qty_to_invoice", "line_ids.qty_invoiced", "line_ids.quantity"
    )
    def _compute_invoice_status(self):
        for order in self:
            lines = order.line_ids
            if order.state != "purchase":
                order.invoice_status = "nothing"
            elif any(line.qty_to_invoice > 0 for line in lines):
                order.invoice_status = "to_invoice"
            elif lines and all(line.qty_invoiced >= line.quantity for line in lines):
                order.invoice_status = "invoiced"
            else:
                order.invoice_status = "nothing"

    def action_cancel(self):
        if self.invoice_ids.filtered(lambda invoice: invoice.state != "cancel"):
            raise UserError(
                self.env._("Cancel the vendor bills of the order before cancelling it.")
            )
        return super().action_cancel()

    def action_create_bill(self):
        """Create a draft vendor bill of what can be billed on each order."""
        bills = self._create_bills()
        return bills._get_records_action(name=self.env._("Vendor Bills"))

    def action_view_bills(self):
        self.ensure_one()
        return self.invoice_ids._get_records_action(name=self.env._("Vendor Bills"))

    def _create_bills(self):
        values = []
        for order in self:
            lines = order.line_ids.filtered(lambda line: line.qty_to_invoice > 0)
            if lines:
                values.append(order._prepare_bill_values(lines))
        if not values:
            raise UserError(
                self.env._("There is nothing to bill: goods are billed once received.")
            )
        return self.env["nme.invoice"].create(values)

    def _prepare_bill_values(self, lines):
        self.ensure_one()
        return {
            "move_type": "in_invoice",
            "partner_id": self.partner_id.id,
            "company_id": self.company_id.id,
            "user_id": self.user_id.id,
            "payment_term_id": self.payment_term_id.id,
            "purchase_order_id": self.id,
            "ref": self.partner_ref,
            "line_ids": [
                Command.create(
                    {
                        "product_id": line.product_id.id,
                        "name": line.name,
                        "quantity": line.qty_to_invoice,
                        "price_unit": line.price_unit,
                        "discount": line.discount,
                        "tax_ids": [Command.set(line.tax_ids.ids)],
                        "purchase_line_id": line.id,
                    }
                )
                for line in lines
            ],
        }
