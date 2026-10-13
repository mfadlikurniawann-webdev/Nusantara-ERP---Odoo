import io

import xlsxwriter

from odoo import fields, models
from odoo.exceptions import UserError
from odoo.tools import BinaryBytes


class NmeReportExport(models.TransientModel):
    """Export a report to an Excel file, or print the aging report as PDF."""

    _name = "nme.report.export"
    _description = "Export Report"

    report_type = fields.Selection(
        [
            ("stock", "Stock by Warehouse"),
            ("receivable", "Receivable Aging"),
            ("payable", "Payable Aging"),
            ("sales", "Sales by Product"),
        ],
        string="Report",
        required=True,
        default="stock",
    )
    company_id = fields.Many2one(
        "res.company", required=True, default=lambda self: self.env.company
    )
    warehouse_id = fields.Many2one(
        "nme.warehouse",
        domain="[('company_id', '=', company_id)]",
        help="Leave empty for every warehouse.",
    )
    date_from = fields.Date(
        default=lambda self: fields.Date.context_today(self).replace(day=1)
    )
    date_to = fields.Date(default=fields.Date.context_today)
    file_data = fields.Binary(string="File", readonly=True, attachment=False)
    file_name = fields.Char(readonly=True)

    def action_export_xlsx(self):
        self.ensure_one()
        title, headers, rows = getattr(self, f"_get_{self.report_type}_rows")()
        self.write(
            {
                "file_data": BinaryBytes(self._build_xlsx(title, headers, rows)),
                "file_name": f"{title}.xlsx",
            }
        )
        return {
            "type": "ir.actions.act_url",
            "url": (
                f"/web/content/{self._name}/{self.id}/file_data/"
                f"{self.file_name}?download=true"
            ),
            "target": "self",
        }

    def action_print_pdf(self):
        self.ensure_one()
        if self.report_type not in ("receivable", "payable"):
            raise UserError(self.env._("Only the aging reports can be printed as PDF."))
        return self.env.ref("nme_reporting.action_report_nme_aging").report_action(self)

    def _build_xlsx(self, title, headers, rows):
        """Return the content of a one-sheet workbook. ``headers`` holds
        (label, kind) pairs where kind is "text", "number" or "money"."""
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {"in_memory": True})
        sheet = workbook.add_worksheet(title[:31])
        bold = workbook.add_format({"bold": True})
        header = workbook.add_format(
            {"bold": True, "bg_color": "#1F6F78", "color": "white"}
        )
        formats = {
            "text": None,
            "number": workbook.add_format({"num_format": "#,##0.00"}),
            "money": workbook.add_format({"num_format": "#,##0"}),
        }
        sheet.write(0, 0, title, bold)
        sheet.write(1, 0, self.company_id.name)
        for col, (label, kind) in enumerate(headers):
            sheet.write(3, col, label, header)
            sheet.set_column(col, col, 24 if kind == "text" else 16)
        for row_index, row in enumerate(rows, start=4):
            for col, value in enumerate(row):
                sheet.write(row_index, col, value, formats[headers[col][1]])
        workbook.close()
        return output.getvalue()

    def _get_stock_rows(self):
        domain = [("company_id", "=", self.company_id.id)]
        if self.warehouse_id:
            domain.append(("warehouse_id", "=", self.warehouse_id.id))
        lines = self.env["nme.stock.report"].search(domain)
        headers = [
            (self.env._("Warehouse"), "text"),
            (self.env._("Location"), "text"),
            (self.env._("Product"), "text"),
            (self.env._("Quantity"), "number"),
            (self.env._("Unit"), "text"),
            (self.env._("Average Cost"), "money"),
            (self.env._("Value"), "money"),
        ]
        rows = [
            (
                line.warehouse_id.name,
                line.location_id.display_name,
                line.product_id.display_name,
                line.quantity,
                line.uom_id.code,
                line.avg_cost,
                line.value,
            )
            for line in lines
        ]
        return self.env._("Stock by Warehouse"), headers, rows

    def _get_aging_rows(self, move_type, title):
        lines = self.env["nme.invoice.aging.report"].search(
            [("move_type", "=", move_type), ("company_id", "=", self.company_id.id)]
        )
        labels = dict(lines._fields["aging_bucket"]._description_selection(self.env))
        headers = [
            (self.env._("Partner"), "text"),
            (self.env._("Invoice"), "text"),
            (self.env._("Due Date"), "text"),
            (self.env._("Days Overdue"), "number"),
            (self.env._("Aging"), "text"),
            (self.env._("Amount Due"), "money"),
        ]
        rows = [
            (
                line.partner_id.display_name,
                line.invoice_id.display_name,
                fields.Date.to_string(line.invoice_date_due),
                line.days_overdue,
                labels.get(line.aging_bucket),
                line.amount_residual,
            )
            for line in lines
        ]
        return title, headers, rows

    def _get_receivable_rows(self):
        return self._get_aging_rows("out_invoice", self.env._("Receivable Aging"))

    def _get_payable_rows(self):
        return self._get_aging_rows("in_invoice", self.env._("Payable Aging"))

    def _get_sales_rows(self):
        domain = [("company_id", "=", self.company_id.id)]
        if self.date_from:
            domain.append(("date", ">=", fields.Datetime.to_datetime(self.date_from)))
        if self.date_to:
            end = fields.Datetime.to_datetime(self.date_to).replace(
                hour=23, minute=59, second=59
            )
            domain.append(("date", "<=", end))
        groups = self.env["nme.sale.report"]._read_group(
            domain,
            ["product_id"],
            [
                "qty_ordered:sum",
                "qty_delivered:sum",
                "amount_untaxed:sum",
                "cost:sum",
                "margin:sum",
            ],
        )
        headers = [
            (self.env._("Product"), "text"),
            (self.env._("Quantity Ordered"), "number"),
            (self.env._("Quantity Delivered"), "number"),
            (self.env._("Untaxed Total"), "money"),
            (self.env._("Cost of Goods"), "money"),
            (self.env._("Margin"), "money"),
        ]
        rows = [
            (product.display_name, ordered, delivered, untaxed, cost, margin)
            for product, ordered, delivered, untaxed, cost, margin in groups
        ]
        return self.env._("Sales by Product"), headers, rows
