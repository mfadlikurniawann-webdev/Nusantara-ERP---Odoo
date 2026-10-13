from odoo import fields, models


class NmePicking(models.Model):
    _inherit = "nme.picking"

    purchase_id = fields.Many2one(
        "nme.purchase.order",
        string="Purchase Order",
        readonly=True,
        copy=False,
        index="btree_not_null",
        check_company=True,
    )

    def _prepare_return_values(self):
        """Keep the purchase order link: returns reduce the received quantity."""
        values = super()._prepare_return_values()
        values["purchase_id"] = self.purchase_id.id
        Move = self.env["nme.stock.move"]
        for command in values["move_ids"]:
            origin = Move.browse(command[2]["origin_returned_move_id"])
            command[2]["purchase_line_id"] = origin.purchase_line_id.id
        return values
