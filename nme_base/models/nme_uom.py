from odoo import fields, models


class NmeUom(models.Model):
    """Unit of measure of a product (kg, sack, box...).

    Units are deliberately simple: one unit per product and no conversion
    between units (see the roadmap in the README).
    """

    _name = "nme.uom"
    _description = "Unit of Measure"
    _order = "sequence, id"

    name = fields.Char(required=True, translate=True)
    code = fields.Char(
        required=True,
        help="Short symbol printed on documents, for example kg or pcs.",
    )
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)

    _code_unique = models.UniqueIndex("(code)", "The unit code must be unique.")
