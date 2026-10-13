from odoo import api, fields, models
from odoo.tools import float_is_zero


class NmeStockAdjustmentLine(models.Model):
    _name = "nme.stock.adjustment.line"
    _description = "Stock Adjustment Line"
    _order = "adjustment_id, id"
    _check_company_auto = True

    adjustment_id = fields.Many2one(
        "nme.stock.adjustment", required=True, index=True, ondelete="cascade"
    )
    company_id = fields.Many2one(related="adjustment_id.company_id", store=True)
    currency_id = fields.Many2one(related="company_id.currency_id")
    state = fields.Selection(related="adjustment_id.state")
    product_id = fields.Many2one(
        "nme.product",
        required=True,
        index=True,
        check_company=True,
        domain=[("type", "=", "goods")],
    )
    uom_id = fields.Many2one(related="product_id.uom_id", string="Unit")
    theoretical_qty = fields.Float(
        string="System Quantity",
        digits="Nusantara Quantity",
        compute="_compute_theoretical_qty",
        store=True,
        help="Quantity in the system when the line was added; refreshed at validation.",
    )
    counted_qty = fields.Float(string="Counted Quantity", digits="Nusantara Quantity")
    difference_qty = fields.Float(
        string="Difference",
        digits="Nusantara Quantity",
        compute="_compute_difference_qty",
        store=True,
    )
    unit_cost = fields.Monetary(
        compute="_compute_unit_cost",
        store=True,
        readonly=False,
        help="Cost of the units added to the stock when the difference is positive.",
    )

    _product_unique = models.UniqueIndex(
        "(adjustment_id, product_id)",
        "A product can only be counted once per adjustment.",
    )
    _counted_qty_positive = models.Constraint(
        "CHECK(counted_qty >= 0)", "The counted quantity cannot be negative."
    )

    @api.depends("product_id", "adjustment_id.location_id")
    def _compute_theoretical_qty(self):
        for line in self:
            location = line.adjustment_id.location_id
            if line.product_id._origin and location:
                product = line.product_id._origin
                line.theoretical_qty = product._get_quantities(location)[product.id]
            else:
                line.theoretical_qty = 0.0

    @api.depends("counted_qty", "theoretical_qty")
    def _compute_difference_qty(self):
        for line in self:
            line.difference_qty = line.counted_qty - line.theoretical_qty

    @api.depends("product_id")
    def _compute_unit_cost(self):
        for line in self:
            product = line.product_id.with_company(line.company_id or self.env.company)
            line.unit_cost = product.avg_cost or product.purchase_price

    def _refresh_theoretical_qty(self):
        """Use the stock at validation time: it may have moved since counting."""
        for line in self:
            location = line.adjustment_id.location_id
            line.theoretical_qty = line.product_id._get_quantities(location)[
                line.product_id.id
            ]

    def _prepare_move_values(self):
        precision = self.env["decimal.precision"].precision_get("Nusantara Quantity")
        loss = self.env["nme.stock.adjustment"]._get_inventory_loss_location()
        values = []
        for line in self:
            if float_is_zero(line.difference_qty, precision_digits=precision):
                continue
            stock = line.adjustment_id.location_id
            incoming = line.difference_qty > 0
            values.append(
                {
                    "name": line.adjustment_id.reason_id.name,
                    "product_id": line.product_id.id,
                    "quantity": abs(line.difference_qty),
                    "location_id": (loss if incoming else stock).id,
                    "location_dest_id": (stock if incoming else loss).id,
                    "adjustment_id": line.adjustment_id.id,
                    "company_id": line.company_id.id,
                    "price_unit": line.unit_cost if incoming else 0.0,
                }
            )
        return values
