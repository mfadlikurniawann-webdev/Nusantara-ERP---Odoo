from odoo import api, fields, models
from odoo.exceptions import UserError

# Fields frozen once the order is confirmed (the delivery was created from them).
LOCKED_FIELDS = {"product_id", "quantity", "price_unit", "discount", "tax_ids"}


class NmeSaleOrderLine(models.Model):
    _name = "nme.sale.order.line"
    _description = "Sales Order Line"
    _inherit = ["nme.trade.line.mixin"]

    order_id = fields.Many2one(
        "nme.sale.order", required=True, index=True, ondelete="cascade"
    )
    company_id = fields.Many2one(related="order_id.company_id", store=True)
    currency_id = fields.Many2one(related="order_id.currency_id", store=True)
    state = fields.Selection(related="order_id.state", store=True)
    partner_id = fields.Many2one(
        related="order_id.partner_id", string="Customer", store=True, index=True
    )
    move_ids = fields.One2many("nme.stock.move", "sale_line_id", string="Stock Moves")
    qty_delivered = fields.Float(
        string="Delivered",
        digits="Nusantara Quantity",
        compute="_compute_qty_delivered",
        store=True,
    )

    @api.depends(
        "move_ids.state",
        "move_ids.quantity",
        "move_ids.location_usage",
        "move_ids.location_dest_usage",
    )
    def _compute_qty_delivered(self):
        for line in self:
            qty = 0.0
            for move in line.move_ids.filtered(lambda m: m.state == "done"):
                if move.location_dest_usage == "customer":
                    qty += move.quantity
                elif move.location_usage == "customer":
                    # Goods returned by the customer.
                    qty -= move.quantity
            line.qty_delivered = qty

    def write(self, vals):
        if LOCKED_FIELDS & vals.keys() and any(
            line.order_id.state in ("sale", "cancel") for line in self
        ):
            raise UserError(
                self.env._("The lines of a confirmed or cancelled order are locked.")
            )
        return super().write(vals)

    @api.ondelete(at_uninstall=False)
    def _unlink_except_confirmed(self):
        if any(line.order_id.state == "sale" for line in self):
            raise UserError(self.env._("Lines of a confirmed order cannot be deleted."))

    def _get_product_price(self):
        return self.product_id.list_price

    def _get_product_taxes(self):
        company = self.order_id.company_id or self.env.company
        return self.product_id._get_company_taxes("sale", company)
