from odoo import api, fields, models
from odoo.exceptions import UserError
from odoo.fields import Command


class NmeSaleOrder(models.Model):
    """Invoicing of sales orders: goods are invoiced on the delivered quantity,
    services on the ordered quantity."""

    _inherit = "nme.sale.order"

    invoice_ids = fields.One2many("nme.invoice", "sale_order_id", string="Invoices")
    invoice_count = fields.Integer(compute="_compute_invoice_count")
    invoice_status = fields.Selection(
        [
            ("nothing", "Nothing to Invoice"),
            ("to_invoice", "To Invoice"),
            ("invoiced", "Fully Invoiced"),
        ],
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
            if order.state != "sale":
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
                self.env._("Cancel the invoices of the order before cancelling it.")
            )
        return super().action_cancel()

    def action_create_invoice(self):
        """Create a draft invoice of what can be invoiced on each order."""
        invoices = self._create_invoices()
        return invoices._get_records_action(name=self.env._("Invoices"))

    def action_view_invoices(self):
        self.ensure_one()
        return self.invoice_ids._get_records_action(name=self.env._("Invoices"))

    def _create_invoices(self):
        values = []
        for order in self:
            lines = order.line_ids.filtered(lambda line: line.qty_to_invoice > 0)
            if lines:
                values.append(order._prepare_invoice_values(lines))
        if not values:
            raise UserError(
                self.env._(
                    "There is nothing to invoice: goods are invoiced once delivered."
                )
            )
        return self.env["nme.invoice"].create(values)

    def _prepare_invoice_values(self, lines):
        self.ensure_one()
        return {
            "move_type": "out_invoice",
            "partner_id": self.partner_id.id,
            "company_id": self.company_id.id,
            "user_id": self.user_id.id,
            "payment_term_id": self.payment_term_id.id,
            "sale_order_id": self.id,
            "ref": self.name,
            "line_ids": [
                Command.create(
                    {
                        "product_id": line.product_id.id,
                        "name": line.name,
                        "quantity": line.qty_to_invoice,
                        "price_unit": line.price_unit,
                        "discount": line.discount,
                        "tax_ids": [Command.set(line.tax_ids.ids)],
                        "sale_line_id": line.id,
                    }
                )
                for line in lines
            ],
        }
