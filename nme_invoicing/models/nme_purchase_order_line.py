from odoo import api, fields, models


class NmePurchaseOrderLine(models.Model):
    _inherit = "nme.purchase.order.line"

    invoice_line_ids = fields.One2many(
        "nme.invoice.line", "purchase_line_id", string="Bill Lines"
    )
    qty_invoiced = fields.Float(
        string="Billed",
        digits="Nusantara Quantity",
        compute="_compute_qty_invoiced",
        store=True,
    )
    qty_to_invoice = fields.Float(
        string="To Bill",
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
        "qty_invoiced", "qty_received", "quantity", "product_id", "order_id.state"
    )
    def _compute_qty_to_invoice(self):
        for line in self:
            if line.order_id.state != "purchase":
                line.qty_to_invoice = 0.0
                continue
            # Billing policy: goods once received, services as ordered.
            billable = (
                line.qty_received if line.product_id.type == "goods" else line.quantity
            )
            line.qty_to_invoice = max(billable - line.qty_invoiced, 0.0)
