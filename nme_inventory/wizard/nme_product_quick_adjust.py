from odoo import api, fields, models


class NmeProductQuickAdjust(models.TransientModel):
    """Set the counted quantity of one product from its form.

    It creates and validates a one-line stock adjustment, so the change still
    goes through the ledger and keeps its reason.
    """

    _name = "nme.product.quick.adjust"
    _description = "Quick Stock Adjustment"

    product_id = fields.Many2one(
        "nme.product",
        required=True,
        domain=[("type", "=", "goods")],
        default=lambda self: self.env.context.get("active_id"),
    )
    company_id = fields.Many2one(
        "res.company", required=True, default=lambda self: self.env.company
    )
    currency_id = fields.Many2one(related="company_id.currency_id")
    warehouse_id = fields.Many2one(
        "nme.warehouse",
        required=True,
        domain="[('company_id', '=', company_id)]",
        default=lambda self: self.env["nme.picking"]._default_warehouse_id(),
    )
    current_qty = fields.Float(
        string="Current Quantity",
        digits="Nusantara Quantity",
        compute="_compute_current_qty",
    )
    counted_qty = fields.Float(
        string="Counted Quantity", digits="Nusantara Quantity", required=True
    )
    reason_id = fields.Many2one("nme.stock.adjustment.reason", required=True)
    unit_cost = fields.Monetary(
        help="Cost of the units added when the counted quantity is higher."
    )

    @api.depends("product_id", "warehouse_id")
    def _compute_current_qty(self):
        for wizard in self:
            location = wizard.warehouse_id.lot_stock_id
            product = wizard.product_id
            wizard.current_qty = (
                product._get_quantities(location)[product.id] if product else 0.0
            )

    @api.onchange("product_id")
    def _onchange_product_id(self):
        product = self.product_id.with_company(self.company_id)
        self.unit_cost = product.avg_cost or product.purchase_price

    def action_apply(self):
        self.ensure_one()
        adjustment = self.env["nme.stock.adjustment"].create(
            {
                "warehouse_id": self.warehouse_id.id,
                "company_id": self.company_id.id,
                "reason_id": self.reason_id.id,
                "line_ids": [
                    fields.Command.create(
                        {
                            "product_id": self.product_id.id,
                            "counted_qty": self.counted_qty,
                            "unit_cost": self.unit_cost,
                        }
                    )
                ],
            }
        )
        adjustment.action_validate()
        return {"type": "ir.actions.act_window_close"}
