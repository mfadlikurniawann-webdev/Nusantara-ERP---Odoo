from dateutil.relativedelta import relativedelta

from odoo import api, fields, models
from odoo.tools import format_date

INVENTORY_USER_GROUP = "nme_inventory.nme_group_inventory_user"
INVOICING_USER_GROUP = "nme_invoicing.nme_group_invoicing_user"
PURCHASE_USER_GROUP = "nme_purchase.nme_group_purchase_user"


class NmeDashboard(models.AbstractModel):
    """Figures of the OWL dashboard, computed in one call.

    Every figure is computed with the rights of the current user. Company
    wide figures (receivables, stock, approvals) are only shown to the
    groups in charge of them: other users could only read part of the
    documents and would see misleading totals.
    """

    _name = "nme.dashboard"
    _description = "Nusantara ERP Dashboard"

    @api.model
    def get_dashboard_data(self):
        company = self.env.company
        kpis = []
        kpis += self._get_sales_kpis(company)
        kpis += self._get_invoicing_kpis(company)
        kpis += self._get_operations_kpis(company)
        return {
            "currency_id": company.currency_id.id,
            "kpis": kpis,
            "sales_chart": self._get_sales_chart(company),
        }

    def _kpi(self, key, label, value, model, domain, kind="integer", alert=False):
        return {
            "key": key,
            "label": label,
            "value": value,
            "type": kind,
            "alert": alert,
            "action": {
                "type": "ir.actions.act_window",
                "name": label,
                "res_model": model,
                "views": [[False, "list"], [False, "form"]],
                "domain": domain,
                "target": "current",
            },
        }

    def _sum(self, Model, domain, field_name):
        # SUM over no rows is NULL in SQL: show 0 instead of an empty value.
        return Model._read_group(domain, [], [f"{field_name}:sum"])[0][0] or 0.0

    def _month_start(self):
        return fields.Date.context_today(self).replace(day=1)

    def _get_sales_kpis(self, company):
        SaleOrder = self.env["nme.sale.order"]
        if not SaleOrder.has_access("read"):
            return []
        month_domain = [
            ("state", "=", "sale"),
            ("company_id", "=", company.id),
            ("date_order", ">=", fields.Datetime.to_datetime(self._month_start())),
        ]
        amount = self._sum(SaleOrder, month_domain, "amount_untaxed")
        to_deliver = [
            ("company_id", "=", company.id),
            ("delivery_status", "in", ("to_deliver", "partial")),
        ]
        return [
            self._kpi(
                "sales_month",
                self.env._("Sales This Month"),
                amount,
                "nme.sale.order",
                month_domain,
                kind="monetary",
            ),
            self._kpi(
                "orders_to_deliver",
                self.env._("Orders to Deliver"),
                SaleOrder.search_count(to_deliver),
                "nme.sale.order",
                to_deliver,
            ),
        ]

    def _get_invoicing_kpis(self, company):
        if not self.env.user.has_group(INVOICING_USER_GROUP):
            return []
        Invoice = self.env["nme.invoice"]
        open_domain = [
            ("state", "=", "posted"),
            ("payment_state", "!=", "paid"),
            ("company_id", "=", company.id),
        ]
        receivable = [*open_domain, ("move_type", "=", "out_invoice")]
        payable = [*open_domain, ("move_type", "=", "in_invoice")]
        overdue = [*receivable, ("is_overdue", "=", True)]
        overdue_count = Invoice.search_count(overdue)
        return [
            self._kpi(
                "receivable",
                self.env._("Receivables Due"),
                self._sum(Invoice, receivable, "amount_residual"),
                "nme.invoice",
                receivable,
                kind="monetary",
            ),
            self._kpi(
                "overdue",
                self.env._("Overdue (%s invoices)", overdue_count),
                self._sum(Invoice, overdue, "amount_residual"),
                "nme.invoice",
                overdue,
                kind="monetary",
                alert=bool(overdue_count),
            ),
            self._kpi(
                "payable",
                self.env._("Payables Due"),
                self._sum(Invoice, payable, "amount_residual"),
                "nme.invoice",
                payable,
                kind="monetary",
            ),
        ]

    def _get_operations_kpis(self, company):
        kpis = []
        if self.env.user.has_group(INVENTORY_USER_GROUP):
            low_stock = self.env["nme.product"].search_count(
                [("is_below_min", "=", True)]
            )
            kpis.append(
                self._kpi(
                    "low_stock",
                    self.env._("Products Below Minimum"),
                    low_stock,
                    "nme.product",
                    [("is_below_min", "=", True)],
                    alert=bool(low_stock),
                )
            )
        if self.env.user.has_group(PURCHASE_USER_GROUP):
            PurchaseOrder = self.env["nme.purchase.order"]
            to_approve = [("state", "=", "to_approve"), ("company_id", "=", company.id)]
            count = PurchaseOrder.search_count(to_approve)
            kpis.append(
                self._kpi(
                    "po_to_approve",
                    self.env._("Purchases to Approve"),
                    count,
                    "nme.purchase.order",
                    to_approve,
                    alert=bool(count),
                )
            )
        return kpis

    def _get_sales_chart(self, company):
        """Untaxed sales of the last six months, oldest first."""
        SaleOrder = self.env["nme.sale.order"]
        if not SaleOrder.has_access("read"):
            return None
        first_month = self._month_start() - relativedelta(months=5)
        groups = SaleOrder._read_group(
            [
                ("state", "=", "sale"),
                ("company_id", "=", company.id),
                ("date_order", ">=", fields.Datetime.to_datetime(first_month)),
            ],
            ["date_order:month"],
            ["amount_untaxed:sum"],
        )
        totals = {
            month.date().replace(day=1): amount or 0.0 for month, amount in groups
        }
        months = [first_month + relativedelta(months=offset) for offset in range(6)]
        return [
            {
                "label": format_date(self.env, month, date_format="MMM yyyy"),
                "value": totals.get(month, 0.0),
            }
            for month in months
        ]
