from odoo import fields, models


class ResPartner(models.Model):
    _inherit = "res.partner"

    nme_purchase_order_count = fields.Integer(
        string="Purchase Order Count", compute="_compute_nme_purchase_order_count"
    )

    def _compute_nme_purchase_order_count(self):
        counts = dict(
            self.env["nme.purchase.order"]._read_group(
                [("partner_id", "in", self.ids)], ["partner_id"], ["__count"]
            )
        )
        for partner in self:
            partner.nme_purchase_order_count = counts.get(partner._origin, 0)

    def action_view_nme_purchase_orders(self):
        self.ensure_one()
        return {
            "name": self.env._("Purchase Orders"),
            "type": "ir.actions.act_window",
            "res_model": "nme.purchase.order",
            "view_mode": "list,form",
            "domain": [("partner_id", "child_of", self.commercial_partner_id.id)],
            "context": {"default_partner_id": self.id},
        }
