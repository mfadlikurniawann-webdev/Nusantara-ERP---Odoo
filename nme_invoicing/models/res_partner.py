from odoo import models


class ResPartner(models.Model):
    _inherit = "res.partner"

    def _get_credit_exposure(self):
        """Confirmed orders not invoiced yet, plus the open customer invoices.

        nme_sales counts the total of the confirmed orders; the part already
        invoiced is replaced by the amount still due on the invoices, which
        also covers invoices created without an order.
        """
        exposure = super()._get_credit_exposure()
        # Same reason as in nme_sales: the check must see every invoice.
        Invoice = self.env["nme.invoice"].sudo()
        domain = [
            ("partner_id", "child_of", self.commercial_partner_id.id),
            ("move_type", "=", "out_invoice"),
            ("state", "!=", "cancel"),
            ("company_id", "=", self.env.company.id),
        ]
        invoiced_orders = Invoice._read_group(
            [*domain, ("sale_order_id.state", "=", "sale")], [], ["amount_total:sum"]
        )[0][0]
        amount_due = Invoice._read_group(domain, [], ["amount_residual:sum"])[0][0]
        return exposure - invoiced_orders + amount_due
