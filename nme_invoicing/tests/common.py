from odoo import Command, fields

from odoo.addons.nme_purchase.tests.common import NmePurchaseCommon
from odoo.addons.nme_sales.tests.common import NmeSalesCommon


class NmeInvoicingCommon(NmeSalesCommon, NmePurchaseCommon):
    """Sales and purchase fixtures plus helpers to invoice them."""

    _test_user_groups = (
        *NmeSalesCommon._test_user_groups,
        "nme_purchase.nme_group_purchase_manager",
        "nme_invoicing.nme_group_invoicing_manager",
    )

    def _confirmed_delivered_order(self, qty=2):
        order = self._create_order([(self.product, qty)])
        order.action_confirm()
        order.picking_ids.action_validate()
        return order

    def _create_invoice(
        self, partner=None, lines=None, move_type="out_invoice", **values
    ):
        """Create a draft invoice; ``lines`` is a list of (product, qty, price)."""
        lines = lines if lines is not None else [(self.product, 1, 100000.0)]
        return self.env["nme.invoice"].create(
            {
                "move_type": move_type,
                "partner_id": (partner or self.customer).id,
                "line_ids": [
                    Command.create(
                        {"product_id": product.id, "quantity": qty, "price_unit": price}
                    )
                    for product, qty, price in lines
                ],
                **values,
            }
        )

    def _pay(self, invoice, amount):
        wizard = (
            self.env["nme.payment.register"]
            .with_context(active_id=invoice.id)
            .create({"amount": amount})
        )
        wizard.action_create_payment()
        return invoice.payment_ids.sorted("id")[-1]

    def _today(self):
        return fields.Date.context_today(self.env.user)
