from odoo.exceptions import ValidationError
from odoo.tests import tagged

from .common import NmeBaseCommon


@tagged("post_install", "-at_install")
class TestNmePartner(NmeBaseCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.indonesia = cls.env.ref("base.id")

    def test_indonesian_npwp_is_validated(self):
        """Business requirement covered by Odoo's built-in VAT check."""
        partner = self.env["res.partner"].create(
            {
                "name": "Toko Baru",
                "country_id": self.indonesia.id,
                "vat": "0012345674615000",
            }
        )
        self.assertEqual(partner.vat, "0012345674615000")
        with self.assertRaises(ValidationError):
            self.env["res.partner"].create(
                {"name": "Toko Salah", "country_id": self.indonesia.id, "vat": "12345"}
            )

    def test_customer_and_vendor_flags(self):
        Partner = self.env["res.partner"]
        customer = Partner.create({"name": "Warung", "nme_is_customer": True})
        vendor = Partner.create({"name": "Pabrik", "nme_is_vendor": True})
        customers = Partner.search(
            [("nme_is_customer", "=", True), ("id", "in", (customer | vendor).ids)]
        )
        self.assertEqual(customers, customer)

    def test_payment_terms_are_company_dependent(self):
        term_14 = self.env.ref("nme_base.nme_payment_term_14_days")
        partner = self.env["res.partner"].create(
            {"name": "Toko Dua Cabang", "nme_payment_term_id": term_14.id}
        )
        self.assertEqual(partner.nme_payment_term_id, term_14)
        self.assertFalse(partner.with_company(self.other_company).nme_payment_term_id)
