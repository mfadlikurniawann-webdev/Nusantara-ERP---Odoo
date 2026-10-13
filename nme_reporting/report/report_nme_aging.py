from collections import defaultdict

from odoo import api, fields, models

BUCKETS = ("current", "1_30", "31_60", "61_90", "90_plus")


class ReportNmeAging(models.AbstractModel):
    """Values of the aging PDF: one row per partner, one column per bucket."""

    _name = "report.nme_reporting.report_nme_aging"
    _description = "Aging Report PDF"

    @api.model
    def _get_report_values(self, docids, data=None):
        wizard = self.env["nme.report.export"].browse(docids)[:1]
        move_type = "in_invoice" if wizard.report_type == "payable" else "out_invoice"
        rows = self.env["nme.invoice.aging.report"].search(
            [("move_type", "=", move_type), ("company_id", "=", wizard.company_id.id)]
        )
        amounts = defaultdict(lambda: dict.fromkeys(BUCKETS, 0.0))
        for row in rows:
            amounts[row.partner_id][row.aging_bucket] += row.amount_residual
        lines = [
            {
                "partner": partner,
                "amounts": partner_amounts,
                "total": sum(partner_amounts.values()),
            }
            for partner, partner_amounts in sorted(
                amounts.items(), key=lambda item: item[0].display_name
            )
        ]
        totals = {
            bucket: sum(line["amounts"][bucket] for line in lines) for bucket in BUCKETS
        }
        labels = dict(
            self.env["nme.invoice.aging.report"]
            ._fields["aging_bucket"]
            ._description_selection(self.env)
        )
        return {
            "doc_ids": docids,
            "doc_model": "nme.report.export",
            "docs": wizard,
            "company": wizard.company_id,
            "currency": wizard.company_id.currency_id,
            "title": (
                self.env._("Payable Aging")
                if move_type == "in_invoice"
                else self.env._("Receivable Aging")
            ),
            "date": fields.Date.context_today(self),
            "buckets": [(bucket, labels[bucket]) for bucket in BUCKETS],
            "lines": lines,
            "totals": totals,
            "grand_total": sum(totals.values()),
        }
