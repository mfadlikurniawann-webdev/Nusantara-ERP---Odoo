from odoo import api, fields, models


class NmeSaleOrderLine(models.Model):
    _inherit = "nme.sale.order.line"

    invoice_line_ids = fields.One2many(
        "nme.invoice.line", "sale_line_id", string="Invoice Lines"
    )
    qty_invoiced = fields.Float(
        string="Invoiced",
        digits="Nusantara Quantity",
        compute="_compute_qty_invoiced",
        store=True,
    )
    qty_to_invoice = fields.Float(
        string="To Invoice",
        digits="Nusantara Quantity",
        compute="_compute_qty_to_invoice",
        store=True,
    )

    @api.depends("invoice_line_ids.quantity", "invoice_line_ids.state")
    def _compute_qty_invoiced(self):
        for line in self:
            line.qty_invoiced = sum(
                line.invoice_line_ids.filtered(lambda il: il.state != "cancel").mapped(
                    "quantity"
                )
            )

    @api.depends(
        "qty_invoiced", "qty_delivered", "quantity", "product_id", "order_id.state"
    )
    def _compute_qty_to_invoice(self):
        for line in self:
            if line.order_id.state != "sale":
                line.qty_to_invoice = 0.0
                continue
            # Invoice policy: goods once delivered, services as ordered.
            billable = (
                line.qty_delivered if line.product_id.type == "goods" else line.quantity
            )
            line.qty_to_invoice = max(billable - line.qty_invoiced, 0.0)
