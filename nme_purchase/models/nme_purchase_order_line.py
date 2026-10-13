from odoo import api, fields, models
from odoo.exceptions import UserError

LOCKED_FIELDS = {"product_id", "quantity", "price_unit", "discount", "tax_ids"}


class NmePurchaseOrderLine(models.Model):
    _name = "nme.purchase.order.line"
    _description = "Purchase Order Line"
    _inherit = ["nme.trade.line.mixin"]

    order_id = fields.Many2one(
        "nme.purchase.order", required=True, index=True, ondelete="cascade"
    )
    company_id = fields.Many2one(related="order_id.company_id", store=True)
    currency_id = fields.Many2one(related="order_id.currency_id", store=True)
    state = fields.Selection(related="order_id.state", store=True)
    partner_id = fields.Many2one(
        related="order_id.partner_id", string="Vendor", store=True, index=True
    )
    move_ids = fields.One2many(
        "nme.stock.move", "purchase_line_id", string="Stock Moves"
    )
    qty_received = fields.Float(
        string="Received",
        digits="Nusantara Quantity",
        compute="_compute_qty_received",
        store=True,
    )

    @api.depends(
        "move_ids.state",
        "move_ids.quantity",
        "move_ids.location_usage",
        "move_ids.location_dest_usage",
    )
    def _compute_qty_received(self):
        for line in self:
            qty = 0.0
            for move in line.move_ids.filtered(lambda m: m.state == "done"):
                if move.location_usage == "supplier":
                    qty += move.quantity
                elif move.location_dest_usage == "supplier":
                    # Goods returned to the vendor.
                    qty -= move.quantity
            line.qty_received = qty

    def write(self, vals):
        if LOCKED_FIELDS & vals.keys() and any(
            line.order_id.state in ("to_approve", "purchase", "cancel") for line in self
        ):
            raise UserError(
                self.env._(
                    "The lines of an order waiting for approval, confirmed or "
                    "cancelled are locked."
                )
            )
        return super().write(vals)

    @api.ondelete(at_uninstall=False)
    def _unlink_except_confirmed(self):
        if any(line.order_id.state in ("to_approve", "purchase") for line in self):
            raise UserError(self.env._("Lines of a confirmed order cannot be deleted."))

    def _get_product_price(self):
        return self.product_id.purchase_price

    def _get_product_taxes(self):
        company = self.order_id.company_id or self.env.company
        return self.product_id._get_company_taxes("purchase", company)

    def _get_net_unit_price(self):
        """Unit cost of the goods after discount and without taxes."""
        self.ensure_one()
        if not self.quantity:
            return 0.0
        return self.price_subtotal / self.quantity
