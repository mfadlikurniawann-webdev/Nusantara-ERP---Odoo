from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.tools import float_compare, float_is_zero


class NmeStockMove(models.Model):
    """One line of the stock ledger: a quantity of a product moving between
    two locations.

    The quantity on hand is never stored on the product: it is the sum of the
    done moves entering internal locations minus the done moves leaving them.
    A done move is immutable; corrections are new moves (returns,
    adjustments), which keeps a complete audit trail and the stock at any
    past date.

    Validating a move also values it (``unit_cost``/``value``) and maintains
    the product average cost (AVCO) of its company.
    """

    _name = "nme.stock.move"
    _description = "Stock Move"
    _order = "date desc, id desc"
    _check_company_auto = True

    name = fields.Char(string="Description")
    reference = fields.Char(compute="_compute_reference", store=True, index=True)
    date = fields.Datetime(
        required=True,
        index=True,
        default=fields.Datetime.now,
        help="Date of the move, set to the validation time when it is done.",
    )
    company_id = fields.Many2one(
        "res.company",
        required=True,
        index=True,
        compute="_compute_company_id",
        store=True,
        readonly=False,
        precompute=True,
    )
    currency_id = fields.Many2one(related="company_id.currency_id")
    product_id = fields.Many2one(
        "nme.product",
        required=True,
        index=True,
        ondelete="restrict",
        check_company=True,
        domain=[("type", "=", "goods")],
    )
    uom_id = fields.Many2one(related="product_id.uom_id", string="Unit")
    quantity = fields.Float(digits="Nusantara Quantity", required=True, default=1.0)
    location_id = fields.Many2one(
        "nme.location",
        string="Source Location",
        required=True,
        index=True,
        check_company=True,
        compute="_compute_locations",
        store=True,
        readonly=False,
        precompute=True,
    )
    location_dest_id = fields.Many2one(
        "nme.location",
        string="Destination Location",
        required=True,
        index=True,
        check_company=True,
        compute="_compute_locations",
        store=True,
        readonly=False,
        precompute=True,
    )
    location_usage = fields.Selection(
        related="location_id.usage", string="Source Location Type", store=True
    )
    location_dest_usage = fields.Selection(
        related="location_dest_id.usage",
        string="Destination Location Type",
        store=True,
    )
    state = fields.Selection(
        [("draft", "Draft"), ("done", "Done"), ("cancel", "Cancelled")],
        required=True,
        default="draft",
        copy=False,
        index=True,
    )
    picking_id = fields.Many2one(
        "nme.picking", string="Transfer", index=True, ondelete="cascade"
    )
    adjustment_id = fields.Many2one(
        "nme.stock.adjustment", index=True, ondelete="cascade"
    )
    price_unit = fields.Monetary(
        string="Incoming Unit Cost",
        copy=False,
        help="Cost of one unit entering the stock (purchase price, adjustment "
        "cost or original cost of a returned delivery). Outgoing moves are "
        "valued at the average cost instead.",
    )
    unit_cost = fields.Monetary(readonly=True, copy=False)
    value = fields.Monetary(readonly=True, copy=False)
    origin_returned_move_id = fields.Many2one(
        "nme.stock.move", string="Returned Move", index="btree_not_null", copy=False
    )
    returned_move_ids = fields.One2many(
        "nme.stock.move", "origin_returned_move_id", string="Returns"
    )

    _quantity_positive = models.Constraint(
        "CHECK(quantity > 0)", "The quantity of a stock move must be positive."
    )
    _different_locations = models.Constraint(
        "CHECK(location_id != location_dest_id)",
        "A stock move must go to another location.",
    )

    @api.depends("picking_id.name", "adjustment_id.name")
    def _compute_reference(self):
        for move in self:
            move.reference = move.picking_id.name or move.adjustment_id.name or False

    @api.depends("picking_id.company_id", "adjustment_id.company_id")
    def _compute_company_id(self):
        for move in self:
            move.company_id = (
                move.picking_id.company_id
                or move.adjustment_id.company_id
                or move.company_id
                or self.env.company
            )

    @api.depends("picking_id.location_id", "picking_id.location_dest_id")
    def _compute_locations(self):
        for move in self:
            if move.picking_id:
                move.location_id = move.picking_id.location_id
                move.location_dest_id = move.picking_id.location_dest_id
            else:
                move.location_id = move.location_id
                move.location_dest_id = move.location_dest_id

    @api.constrains("product_id")
    def _check_product_is_goods(self):
        for move in self:
            if move.product_id.type != "goods":
                raise ValidationError(
                    self.env._(
                        "%s is a service: services are not tracked in stock.",
                        move.product_id.display_name,
                    )
                )

    def write(self, vals):
        if any(move.state == "done" for move in self):
            raise UserError(
                self.env._(
                    "Done stock moves cannot be modified. Create a return or a "
                    "stock adjustment to correct the stock."
                )
            )
        return super().write(vals)

    @api.ondelete(at_uninstall=False)
    def _unlink_except_done(self):
        if any(move.state == "done" for move in self):
            raise UserError(self.env._("Done stock moves cannot be deleted."))

    def _action_done(self):
        """Check availability, value the moves and post them to the ledger.

        Moves are processed one by one on purpose: each done move changes the
        quantity on hand and the average cost used by the next one.
        """
        Product = self.env["nme.product"]
        for move in self.filtered(lambda m: m.state == "draft").sorted("id"):
            move._check_availability()
            unit_cost = move._get_unit_cost()
            if move._is_valued_incoming():
                move._update_average_cost(unit_cost)
            move.write(
                {
                    "state": "done",
                    "date": fields.Datetime.now(),
                    "unit_cost": unit_cost,
                    "value": move.currency_id.round(unit_cost * move.quantity),
                }
            )
            Product.invalidate_model(["qty_available", "stock_value", "is_below_min"])
        return True

    def _action_cancel(self):
        if any(move.state == "done" for move in self):
            raise UserError(self.env._("Done stock moves cannot be cancelled."))
        self.write({"state": "cancel"})

    def _check_availability(self):
        """Refuse a move that would make the stock of its source location negative."""
        self.ensure_one()
        if self.location_id.usage != "internal":
            return
        precision = self.env["decimal.precision"].precision_get("Nusantara Quantity")
        available = self.product_id._get_quantities(self.location_id)[
            self.product_id.id
        ]
        if float_compare(available, self.quantity, precision_digits=precision) < 0:
            raise UserError(
                self.env._(
                    "Not enough %(product)s in %(location)s: %(available)s "
                    "available, %(needed)s needed.",
                    product=self.product_id.display_name,
                    location=self.location_id.display_name,
                    available=available,
                    needed=self.quantity,
                )
            )

    def _is_valued_incoming(self):
        """Goods entering the company's stock from outside (vendor, customer
        return or positive adjustment)."""
        return (
            self.location_dest_id.usage == "internal"
            and self.location_id.usage != "internal"
        )

    def _get_unit_cost(self):
        self.ensure_one()
        if self._is_valued_incoming():
            return self.price_unit
        return self.product_id.with_company(self.company_id).avg_cost

    def _update_average_cost(self, unit_cost):
        """Weighted average of the stock on hand and the incoming goods."""
        self.ensure_one()
        product = self.product_id.with_company(self.company_id)
        company_locations = self.env["nme.location"].search(
            [("usage", "=", "internal"), ("company_id", "=", self.company_id.id)]
        )
        qty_before = max(product._get_quantities(company_locations)[product.id], 0.0)
        precision = self.env["decimal.precision"].precision_get("Nusantara Quantity")
        if float_is_zero(qty_before, precision_digits=precision):
            new_cost = unit_cost
        else:
            new_cost = (qty_before * product.avg_cost + self.quantity * unit_cost) / (
                qty_before + self.quantity
            )
        # The average cost is a consequence of validating the move, not a
        # product edit: stock users may update it without product write access.
        product.sudo().avg_cost = new_cost
