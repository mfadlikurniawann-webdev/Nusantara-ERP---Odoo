from odoo import api, models


class ResCompany(models.Model):
    _inherit = "res.company"

    @api.model_create_multi
    def create(self, vals_list):
        """Give every new company a warehouse so it can move stock right away."""
        companies = super().create(vals_list)
        self.env["nme.warehouse"].sudo().create(
            [
                {"name": company.name, "code": "WH", "company_id": company.id}
                for company in companies
            ]
        )
        return companies
