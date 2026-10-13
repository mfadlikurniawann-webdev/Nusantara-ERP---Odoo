from odoo import fields, models, tools
from odoo.tools import SQL


class NmeInvoiceAgingReport(models.Model):
    """Open balance of posted invoices grouped by how late they are.

    A PostgreSQL view evaluated at query time: the aging buckets always use
    the current date, without any scheduled recomputation.
    """

    _name = "nme.invoice.aging.report"
    _description = "Receivable and Payable Aging"
    _auto = False
    _order = "days_overdue desc, invoice_date_due"
    # Flush these fields before reading the view.
    _depends = {
        "nme.invoice": [
            "partner_id",
            "user_id",
            "company_id",
            "currency_id",
            "move_type",
            "invoice_date",
            "invoice_date_due",
            "amount_residual",
            "state",
            "payment_state",
        ],
    }

    invoice_id = fields.Many2one("nme.invoice", readonly=True)
    partner_id = fields.Many2one("res.partner", readonly=True)
    user_id = fields.Many2one("res.users", string="Responsible", readonly=True)
    company_id = fields.Many2one("res.company", readonly=True)
    currency_id = fields.Many2one("res.currency", readonly=True)
    move_type = fields.Selection(
        [("out_invoice", "Receivable"), ("in_invoice", "Payable")],
        string="Type",
        readonly=True,
    )
    invoice_date = fields.Date(readonly=True)
    invoice_date_due = fields.Date(string="Due Date", readonly=True)
    days_overdue = fields.Integer(readonly=True)
    aging_bucket = fields.Selection(
        [
            ("current", "Not Due"),
            ("1_30", "1-30 Days"),
            ("31_60", "31-60 Days"),
            ("61_90", "61-90 Days"),
            ("90_plus", "Over 90 Days"),
        ],
        string="Aging",
        readonly=True,
    )
    amount_residual = fields.Monetary(string="Amount Due", readonly=True)

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute(
            SQL(
                """
                CREATE OR REPLACE VIEW %(table)s AS (
                    SELECT aged.*,
                           GREATEST(aged.late, 0) AS days_overdue,
                           CASE
                               WHEN aged.late <= 0 THEN 'current'
                               WHEN aged.late <= 30 THEN '1_30'
                               WHEN aged.late <= 60 THEN '31_60'
                               WHEN aged.late <= 90 THEN '61_90'
                               ELSE '90_plus'
                           END AS aging_bucket
                      FROM (
                          SELECT inv.id AS id,
                                 inv.id AS invoice_id,
                                 inv.partner_id,
                                 inv.user_id,
                                 inv.company_id,
                                 inv.currency_id,
                                 inv.move_type,
                                 inv.invoice_date,
                                 inv.invoice_date_due,
                                 inv.amount_residual,
                                 CURRENT_DATE - inv.invoice_date_due AS late
                            FROM nme_invoice inv
                           WHERE inv.state = 'posted'
                             AND inv.payment_state != 'paid'
                      ) AS aged
                )
                """,
                table=SQL.identifier(self._table),
            )
        )
