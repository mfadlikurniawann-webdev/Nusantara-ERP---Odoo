from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError

RETURN_TYPES = {"incoming": "outgoing", "outgoing": "incoming", "internal": "internal"}


class NmePicking(models.Model):
    """Transfer of goods: receipt, delivery or transfer between warehouses.

    The source and destination locations are derived from the transfer type
    and the warehouses; each line is a stock move posted to the ledger when
    the transfer is validated.
    """

    _name = "nme.picking"
    _description = "Transfer"
    _inherit = ["nme.document.mixin"]
    _order = "scheduled_date desc, id desc"

    _state_transitions = {
        "draft": {"done", "cancel"},
        "cancel": {"draft"},
    }

    picking_type = fields.Selection(
        [
            ("incoming", "Receipt"),
            ("outgoing", "Delivery"),
            ("internal", "Internal Transfer"),
        ],
        string="Transfer Type",
        required=True,
        default="incoming",
        index=True,
    )
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
    partner_id = fields.Many2one(
        "res.partner", string="Contact", index=True, check_company=True
    )
    warehouse_id = fields.Many2one(
        "nme.warehouse",
        required=True,
        index=True,
        check_company=True,
        default=lambda self: self._default_warehouse_id(),
    )
    warehouse_dest_id = fields.Many2one(
        "nme.warehouse",
        string="Destination Warehouse",
        check_company=True,
        help="Warehouse receiving the goods of an internal transfer.",
    )
    location_id = fields.Many2one(
        "nme.location",
        string="Source Location",
        compute="_compute_locations",
        store=True,
        check_company=True,
    )
    location_dest_id = fields.Many2one(
        "nme.location",
        string="Destination Location",
        compute="_compute_locations",
        store=True,
        check_company=True,
    )
    scheduled_date = fields.Datetime(
        required=True, index=True, default=fields.Datetime.now, tracking=True
    )
    date_done = fields.Datetime(readonly=True, copy=False)
    origin = fields.Char(string="Source Document", index="trigram")
    move_ids = fields.One2many(
        "nme.stock.move", "picking_id", string="Moves", copy=True
    )
    return_of_id = fields.Many2one(
        "nme.picking",
        readonly=True,
        copy=False,
        index="btree_not_null",
    )
    return_ids = fields.One2many("nme.picking", "return_of_id", string="Returns")
    return_count = fields.Integer(compute="_compute_return_count")

    def _default_warehouse_id(self):
        return self.env["nme.warehouse"].search(
            [("company_id", "=", self.env.company.id)], limit=1
        )

    @api.depends(
        "picking_type",
        "warehouse_id.lot_stock_id",
        "warehouse_dest_id.lot_stock_id",
        "return_of_id",
    )
    def _compute_locations(self):
        vendors = self.env.ref("nme_inventory.nme_location_vendors")
        customers = self.env.ref("nme_inventory.nme_location_customers")
        for picking in self:
            stock = picking.warehouse_id.lot_stock_id
            if picking.return_of_id:
                # A return goes back exactly where the goods came from.
                picking.location_id = picking.return_of_id.location_dest_id
                picking.location_dest_id = picking.return_of_id.location_id
            elif picking.picking_type == "incoming":
                picking.location_id, picking.location_dest_id = vendors, stock
            elif picking.picking_type == "outgoing":
                picking.location_id, picking.location_dest_id = stock, customers
            else:
                picking.location_id = stock
                picking.location_dest_id = picking.warehouse_dest_id.lot_stock_id

    def _compute_return_count(self):
        counts = dict(
            self.env["nme.picking"]._read_group(
                [("return_of_id", "in", self.ids)], ["return_of_id"], ["__count"]
            )
        )
        for picking in self:
            picking.return_count = counts.get(picking, 0)

    @api.constrains("picking_type", "warehouse_id", "warehouse_dest_id")
    def _check_internal_destination(self):
        for picking in self:
            if picking.picking_type == "internal" and (
                not picking.warehouse_dest_id
                or picking.warehouse_dest_id == picking.warehouse_id
            ):
                raise ValidationError(
                    self.env._(
                        "Internal transfer %s must go to another warehouse.",
                        picking.display_name,
                    )
                )

    def _get_sequence_code(self, vals):
        return f"nme.picking.{vals.get('picking_type') or 'incoming'}"

    def action_validate(self):
        """Post the moves to the stock ledger and close the transfers."""
        for picking in self:
            if picking.state != "draft":
                raise UserError(
                    self.env._("%s is not a draft transfer.", picking.display_name)
                )
            if not picking.move_ids:
                raise UserError(
                    self.env._("Add at least one product to %s.", picking.display_name)
                )
        self.move_ids._action_done()
        self._set_state("done")
        self.date_done = fields.Datetime.now()
        return True

    def action_cancel(self):
        res = super().action_cancel()
        self.move_ids._action_cancel()
        return res

    def action_set_draft(self):
        self._set_state("draft")
        self.move_ids.write({"state": "draft"})
        return True

    def action_create_return(self):
        """Create the reverse transfer of a done transfer (full return)."""
        self.ensure_one()
        if self.state != "done":
            raise UserError(self.env._("Only done transfers can be returned."))
        if self.return_ids.filtered(lambda p: p.state != "cancel"):
            raise UserError(
                self.env._("%s has already been returned.", self.display_name)
            )
        return_picking = self.create(self._prepare_return_values())
        return {
            "type": "ir.actions.act_window",
            "res_model": "nme.picking",
            "res_id": return_picking.id,
            "view_mode": "form",
            "views": [(False, "form")],
        }

    def _prepare_return_values(self):
        """Values of the return transfer; overridden to keep sales/purchase links."""
        self.ensure_one()
        values = {
            "picking_type": RETURN_TYPES[self.picking_type],
            "partner_id": self.partner_id.id,
            "company_id": self.company_id.id,
            "origin": self.env._("Return of %s", self.name),
            "return_of_id": self.id,
        }
        if self.picking_type == "internal":
            values.update(
                warehouse_id=self.warehouse_dest_id.id,
                warehouse_dest_id=self.warehouse_id.id,
            )
        else:
            values["warehouse_id"] = self.warehouse_id.id
        values["move_ids"] = [
            fields.Command.create(
                {
                    "product_id": move.product_id.id,
                    "quantity": move.quantity,
                    "name": move.name,
                    "origin_returned_move_id": move.id,
                    # A returned delivery comes back at the cost it left with.
                    "price_unit": move.unit_cost,
                }
            )
            for move in self.move_ids.filtered(lambda m: m.state == "done")
        ]
        return values

    def action_view_returns(self):
        self.ensure_one()
        action = {
            "name": self.env._("Returns"),
            "type": "ir.actions.act_window",
            "res_model": "nme.picking",
            "view_mode": "list,form",
            "domain": [("return_of_id", "=", self.id)],
        }
        if self.return_count == 1:
            action.update(
                view_mode="form", views=[(False, "form")], res_id=self.return_ids.id
            )
        return action
