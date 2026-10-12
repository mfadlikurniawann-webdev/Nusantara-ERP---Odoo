from datetime import timedelta

from odoo import fields, models


class NmePaymentTerm(models.Model):
    """Payment term expressed as a number of days after the document date."""

    _name = "nme.payment.term"
    _description = "Payment Term"
    _order = "sequence, days, id"
    _check_company_auto = True

    name = fields.Char(required=True, translate=True)
    days = fields.Integer(string="Due After (Days)", required=True, default=0)
    note = fields.Text(string="Description on Documents", translate=True)
    sequence = fields.Integer(default=10)
    company_id = fields.Many2one(
        "res.company",
        index=True,
        help="Leave empty to share the payment term between companies.",
    )
    active = fields.Boolean(default=True)

    _days_positive = models.Constraint(
        "CHECK(days >= 0)", "The number of days cannot be negative."
    )

    def _get_due_date(self, date_ref):
        """Return the due date of a document dated ``date_ref``."""
        self.ensure_one()
        return date_ref + timedelta(days=self.days)
