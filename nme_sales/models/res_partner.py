from odoo import api, fields, models


class ResPartner(models.Model):
    """Credit limit of customers, per company."""

    _inherit = "res.partner"

    nme_credit_limit = fields.Float(
        string="Credit Limit",
        digits=(16, 2),
        company_dependent=True,
        help="Maximum amount the customer may owe, including confirmed orders.",
    )
    nme_credit_policy = fields.Selection(
        [
            ("none", "No Limit"),
            ("warning", "Warn"),
            ("block", "Block"),
        ],
        string="Credit Limit Policy",
        company_dependent=True,
        help="Warn: confirming above the limit is allowed but logged. "
        "Block: only a sales manager can confirm above the limit.",
    )
    nme_company_currency_id = fields.Many2one(
        "res.currency",
        string="Company Currency",
        compute="_compute_nme_company_currency_id",
    )
    nme_credit_exposure = fields.Float(
        string="Credit Used",
        digits=(16, 2),
        compute="_compute_nme_credit_exposure",
        help="Amount owed or committed by the customer in the current company.",
    )
    nme_sale_order_count = fields.Integer(
        string="Sales Order Count", compute="_compute_nme_sale_order_count"
    )

    @api.depends_context("company")
    def _compute_nme_company_currency_id(self):
        self.nme_company_currency_id = self.env.company.currency_id

    @api.depends_context("company")
    def _compute_nme_credit_exposure(self):
        for partner in self:
            partner.nme_credit_exposure = (
                partner._get_credit_exposure() if partner._origin else 0.0
            )

    def _compute_nme_sale_order_count(self):
        counts = dict(
            self.env["nme.sale.order"]._read_group(
                [("partner_id", "in", self.ids)], ["partner_id"], ["__count"]
            )
        )
        for partner in self:
            partner.nme_sale_order_count = counts.get(partner._origin, 0)

    def _get_credit_exposure(self):
        """Amount the customer owes or committed to buy in the current company.

        This module counts the total of confirmed sales orders; nme_invoicing
        refines it with the open balance of customer invoices.
        """
        self.ensure_one()
        # The credit check must see every order of the customer, also those
        # of other salespeople that the current user cannot read.
        groups = (
            self.env["nme.sale.order"]
            .sudo()
            ._read_group(self._get_credit_order_domain(), [], ["amount_total:sum"])
        )
        return groups[0][0]

    def _get_credit_order_domain(self):
        return [
            ("partner_id", "child_of", self.commercial_partner_id.id),
            ("state", "=", "sale"),
            ("company_id", "=", self.env.company.id),
        ]

    def action_view_nme_sale_orders(self):
        self.ensure_one()
        return {
            "name": self.env._("Sales Orders"),
            "type": "ir.actions.act_window",
            "res_model": "nme.sale.order",
            "view_mode": "list,form",
            "domain": [("partner_id", "child_of", self.commercial_partner_id.id)],
            "context": {"default_partner_id": self.id},
        }
