from odoo import api, fields, models
from odoo.exceptions import ValidationError


class NmeLocation(models.Model):
    """Place where goods are, or where they come from / go to.

    Stock follows a double-entry logic: every stock move goes from one
    location to another. Only ``internal`` locations (inside a warehouse)
    hold stock; the others are virtual counterparts (vendors, customers,
    inventory adjustments) shared by all companies.
    """

    _name = "nme.location"
    _description = "Stock Location"
    _order = "warehouse_id, name, id"
    _rec_name = "complete_name"
    _check_company_auto = True

    name = fields.Char(required=True)
    complete_name = fields.Char(compute="_compute_complete_name", store=True)
    usage = fields.Selection(
        [
            ("internal", "Internal"),
            ("supplier", "Vendor"),
            ("customer", "Customer"),
            ("inventory", "Inventory Adjustment"),
        ],
        string="Location Type",
        required=True,
        default="internal",
        help="Only internal locations hold stock.",
    )
    warehouse_id = fields.Many2one(
        "nme.warehouse", index=True, ondelete="cascade", check_company=True
    )
    company_id = fields.Many2one(
        "res.company",
        index=True,
        help="Empty for virtual locations shared by every company.",
    )
    active = fields.Boolean(default=True)

    @api.depends("name", "warehouse_id.code")
    def _compute_complete_name(self):
        for location in self:
            if location.warehouse_id:
                location.complete_name = f"{location.warehouse_id.code}/{location.name}"
            else:
                location.complete_name = location.name

    @api.constrains("usage", "warehouse_id", "company_id")
    def _check_internal_location(self):
        for location in self:
            if location.usage == "internal" and not (
                location.warehouse_id and location.company_id
            ):
                raise ValidationError(
                    self.env._(
                        "Internal location %s needs a warehouse and a company.",
                        location.display_name,
                    )
                )
