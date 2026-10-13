from odoo import fields, models


class NmePicking(models.Model):
    _inherit = "nme.picking"

    sale_id = fields.Many2one(
        "nme.sale.order",
        string="Sales Order",
        readonly=True,
        copy=False,
        index="btree_not_null",
        check_company=True,
    )

    def _prepare_return_values(self):
        """Keep the link to the sales order so returns reduce the delivered quantity."""
        values = super()._prepare_return_values()
        values["sale_id"] = self.sale_id.id
        Move = self.env["nme.stock.move"]
        for command in values["move_ids"]:
            origin = Move.browse(command[2]["origin_returned_move_id"])
            command[2]["sale_line_id"] = origin.sale_line_id.id
        return values
