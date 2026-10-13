from odoo import api, fields, models
from odoo.exceptions import UserError

LOCKED_FIELDS = {"product_id", "quantity", "price_unit", "discount", "tax_ids"}


class NmeInvoiceLine(models.Model):
    _name = "nme.invoice.line"
    _description = "Invoice Line"
    _inherit = ["nme.trade.line.mixin"]

    invoice_id = fields.Many2one(
        "nme.invoice", required=True, index=True, ondelete="cascade"
    )
    company_id = fields.Many2one(related="invoice_id.company_id", store=True)
    currency_id = fields.Many2one(related="invoice_id.currency_id", store=True)
    move_type = fields.Selection(related="invoice_id.move_type", store=True)
    state = fields.Selection(related="invoice_id.state", store=True)
    partner_id = fields.Many2one(related="invoice_id.partner_id", store=True)
    sale_line_id = fields.Many2one(
        "nme.sale.order.line",
        string="Sales Order Line",
        index="btree_not_null",
        copy=False,
    )
    purchase_line_id = fields.Many2one(
        "nme.purchase.order.line",
        string="Purchase Order Line",
        index="btree_not_null",
        copy=False,
    )

    def write(self, vals):
        if LOCKED_FIELDS & vals.keys() and any(
            line.invoice_id.state != "draft" for line in self
        ):
            raise UserError(self.env._("Only the lines of a draft invoice can change."))
        return super().write(vals)

    @api.ondelete(at_uninstall=False)
    def _unlink_except_posted(self):
        if any(line.invoice_id.state == "posted" for line in self):
            raise UserError(self.env._("Lines of a posted invoice cannot be deleted."))

    def _get_product_price(self):
        if self.invoice_id.move_type == "in_invoice":
            return self.product_id.purchase_price
        return self.product_id.list_price

    def _get_product_taxes(self):
        company = self.invoice_id.company_id or self.env.company
        tax_use = "purchase" if self.invoice_id.move_type == "in_invoice" else "sale"
        return self.product_id._get_company_taxes(tax_use, company)
