from odoo import fields, models


class NmeTax(models.Model):
    """Percentage tax applied on top of the untaxed price (for example VAT 11%).

    Taxes are always price-excluded and never compounded: every rate applies
    on the same untaxed base.
    """

    _name = "nme.tax"
    _description = "Tax"
    _order = "sequence, id"
    _check_company_auto = True

    name = fields.Char(required=True, translate=True)
    amount = fields.Float(string="Rate (%)", required=True, digits=(16, 4))
    type_tax_use = fields.Selection(
        [("sale", "Sales"), ("purchase", "Purchases")],
        string="Tax Scope",
        required=True,
        default="sale",
    )
    sequence = fields.Integer(default=10)
    company_id = fields.Many2one(
        "res.company",
        required=True,
        index=True,
        default=lambda self: self.env.company,
    )
    active = fields.Boolean(default=True)

    _amount_range = models.Constraint(
        "CHECK(amount >= 0 AND amount <= 100)",
        "A tax rate must be between 0 and 100%.",
    )

    def _get_tax_amount(self, base_amount, currency):
        """Return the total tax of ``self`` applied on ``base_amount``.

        Each tax is rounded separately in ``currency``, the way it is printed
        on documents.
        """
        return sum(currency.round(base_amount * tax.amount / 100.0) for tax in self)
