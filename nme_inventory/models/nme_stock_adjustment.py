from odoo import api, fields, models
from odoo.exceptions import UserError

MANAGER_GROUP = "nme_inventory.nme_group_inventory_manager"


class NmeStockAdjustment(models.Model):
    """Stock count of a warehouse (stock opname) with a mandatory reason.

    Users record the counted quantities; a manager validates the adjustment,
    which posts one stock move per difference against the virtual
    "Inventory Adjustment" location.
    """

    _name = "nme.stock.adjustment"
    _description = "Stock Adjustment"
    _inherit = ["nme.document.mixin"]
    _order = "date desc, id desc"

    _state_transitions = {
        "draft": {"done", "cancel"},
        "cancel": {"draft"},
    }

    state = fields.Selection(
        [("draft", "Draft"), ("done", "Done"), ("cancel", "Cancelled")],
        string="Status",
        required=True,
        readonly=True,
        copy=False,
        index=True,
        tracking=True,
        default="draft",
    )
    date = fields.Date(required=True, default=fields.Date.context_today, tracking=True)
    warehouse_id = fields.Many2one(
        "nme.warehouse",
        required=True,
        check_company=True,
        tracking=True,
        default=lambda self: self.env["nme.picking"]._default_warehouse_id(),
    )
    location_id = fields.Many2one(related="warehouse_id.lot_stock_id")
    reason_id = fields.Many2one(
        "nme.stock.adjustment.reason", required=True, tracking=True
    )
    line_ids = fields.One2many(
        "nme.stock.adjustment.line", "adjustment_id", string="Lines", copy=True
    )
    move_ids = fields.One2many("nme.stock.move", "adjustment_id", string="Moves")

    def action_load_products(self):
        """Add a line for every product currently in stock in the warehouse."""
        self.ensure_one()
        products = self.env["nme.product"].search([("type", "=", "goods")])
        quantities = products._get_quantities(self.location_id)
        missing = products.filtered(
            lambda p: quantities[p.id] and p not in self.line_ids.product_id
        )
        self.env["nme.stock.adjustment.line"].create(
            [
                {
                    "adjustment_id": self.id,
                    "product_id": product.id,
                    "counted_qty": quantities[product.id],
                }
                for product in missing
            ]
        )
        return True

    def action_validate(self):
        if not self.env.user.has_group(MANAGER_GROUP):
            raise UserError(
                self.env._("Only inventory managers can validate stock adjustments.")
            )
        for adjustment in self:
            if adjustment.state != "draft":
                raise UserError(
                    self.env._("%s is not a draft adjustment.", adjustment.display_name)
                )
            if not adjustment.line_ids:
                raise UserError(
                    self.env._("Add at least one line to %s.", adjustment.display_name)
                )
        lines = self.line_ids
        lines._refresh_theoretical_qty()
        moves = self.env["nme.stock.move"].create(lines._prepare_move_values())
        moves._action_done()
        self._set_state("done")
        return True

    @api.model
    def _get_inventory_loss_location(self):
        return self.env.ref("nme_inventory.nme_location_inventory_loss")
