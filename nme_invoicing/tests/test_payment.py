from odoo.exceptions import UserError, ValidationError
from odoo.tests import Form, new_test_user, tagged

from .common import NmeInvoicingCommon


@tagged("post_install", "-at_install")
class TestNmePayment(NmeInvoicingCommon):
    def test_partial_then_full_payment(self):
        invoice = self._create_invoice()  # 100,000 + 11% = 111,000
        invoice.action_post()
        self.assertEqual(invoice.payment_state, "not_paid")

        wizard_form = Form(
            self.env["nme.payment.register"].with_context(active_id=invoice.id)
        )
        self.assertEqual(wizard_form.amount, 111000.0)
        self.assertEqual(wizard_form.memo, invoice.name)
        wizard_form.amount = 50000.0
        wizard_form.save().action_create_payment()
        payment = invoice.payment_ids
        self.assertTrue(payment.name.startswith("PAY/"))
        self.assertEqual(payment.payment_type, "inbound")
        self.assertEqual(invoice.payment_state, "partial")
        self.assertEqual(invoice.amount_residual, 61000.0)

        self._pay(invoice, 61000.0)
        self.assertEqual(invoice.payment_state, "paid")
        self.assertEqual(invoice.amount_residual, 0.0)
        self.assertFalse(invoice.is_overdue)

    def test_invoice_cannot_be_overpaid(self):
        invoice = self._create_invoice()
        invoice.action_post()
        with self.assertRaises(UserError):
            self._pay(invoice, 200000.0)
        with self.assertRaises(ValidationError):
            self.env["nme.payment"].create(
                {"invoice_id": invoice.id, "amount": 200000.0}
            )

    def test_only_posted_invoices_can_be_paid(self):
        invoice = self._create_invoice()
        with self.assertRaises(UserError):
            invoice.action_register_payment()

    def test_cancel_payment_and_reset_invoice(self):
        invoice = self._create_invoice()
        invoice.action_post()
        payment = self._pay(invoice, 111000.0)
        with self.assertRaises(UserError):
            invoice.action_draft()
        with self.assertRaises(UserError):
            invoice.action_cancel()
        payment.action_cancel()
        self.assertEqual(invoice.payment_state, "not_paid")
        with self.assertRaises(UserError):
            payment.unlink()
        invoice.action_draft()
        self.assertEqual(invoice.state, "draft")

    def test_invoicing_user_restrictions(self):
        accountant = new_test_user(
            self.env,
            login="nme_accountant",
            groups="nme_invoicing.nme_group_invoicing_user",
        )
        invoice = self._create_invoice().with_user(accountant)
        invoice.action_post()
        payment = self._pay(invoice, 10000.0).with_user(accountant)
        with self.assertRaises(UserError):
            payment.action_cancel()
        with self.assertRaises(UserError):
            invoice.action_cancel()
        with self.assertRaises(UserError):
            invoice.action_draft()

    def test_vendor_bill_payment_is_outbound(self):
        bill = self._create_invoice(
            partner=self.vendor,
            move_type="in_invoice",
            lines=[(self.product, 1, 80000.0)],
        )
        bill.action_post()
        payment = self._pay(bill, bill.amount_total)
        self.assertEqual(payment.payment_type, "outbound")
        self.assertEqual(bill.payment_state, "paid")
