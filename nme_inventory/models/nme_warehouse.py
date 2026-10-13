from odoo import api, fields, models


class NmeWarehouse(models.Model):
    """Physical warehouse. Its main stock location is created automatically."""

    _name = "nme.warehouse"
    _description = "Warehouse"
    _order = "sequence, id"
    _check_company_auto = True

    name = fields.Char(required=True)
    code = fields.Char(
        string="Short Name",
        required=True,
        size=5,
        help="Prefix of the warehouse locations, for example SBY.",
    )
    sequence = fields.Integer(default=10)
    company_id = fields.Many2one(
        "res.company",
        required=True,
        index=True,
        default=lambda self: self.env.company,
    )
    partner_id = fields.Many2one("res.partner", string="Address", check_company=True)
    lot_stock_id = fields.Many2one(
        "nme.location",
        string="Stock Location",
        readonly=True,
        check_company=True,
        help="Main internal location of the warehouse, created with it.",
    )
    location_ids = fields.One2many("nme.location", "warehouse_id", string="Locations")
    active = fields.Boolean(default=True)

    _code_company_unique = models.UniqueIndex(
        "(code, company_id)", "The warehouse short name must be unique per company."
    )

    @api.model_create_multi
    def create(self, vals_list):
        warehouses = super().create(vals_list)
        locations = self.env["nme.location"].create(
            [
                {
                    "name": self.env._("Stock"),
                    "usage": "internal",
                    "warehouse_id": warehouse.id,
                    "company_id": warehouse.company_id.id,
                }
                for warehouse in warehouses
            ]
        )
        for warehouse, location in zip(warehouses, locations, strict=True):
            warehouse.lot_stock_id = location
        return warehouses

    def write(self, vals):
        res = super().write(vals)
        if "company_id" in vals:
            self.location_ids.company_id = vals["company_id"]
        return res
