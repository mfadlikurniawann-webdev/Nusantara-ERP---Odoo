from psycopg2 import IntegrityError

from odoo.exceptions import UserError
from odoo.tests import tagged
from odoo.tools import mute_logger

from .common import NmeBaseCommon


@tagged("post_install", "-at_install")
class TestNmeProduct(NmeBaseCommon):
    def test_defaults_come_from_company_settings(self):
        product = self.env["nme.product"].create({"name": "Sugar"})
        self.assertEqual(product.sale_tax_ids, self.tax_sale)
        self.assertEqual(product.purchase_tax_ids, self.tax_purchase)
        self.assertEqual(product.uom_id, self.uom_unit)
        self.assertEqual(product.currency_id, self.company.currency_id)

    def test_shared_product_keeps_taxes_per_company(self):
        other_company = self.other_company
        other_tax = self.env["nme.tax"].create(
            {"name": "Branch VAT", "amount": 11.0, "company_id": other_company.id}
        )
        self.product.sale_tax_ids |= other_tax
        self.assertEqual(
            self.product._get_company_taxes("sale", self.company), self.tax_sale
        )
        self.assertEqual(
            self.product._get_company_taxes("sale", other_company), other_tax
        )
        self.assertEqual(
            self.product._get_company_taxes("purchase", self.company),
            self.tax_purchase,
        )

    def test_display_name_and_search_use_internal_reference(self):
        self.assertEqual(self.product.display_name, "[TST-1] Test Rice")
        no_code = self.env["nme.product"].create({"name": "No Code"})
        self.assertEqual(no_code.display_name, "No Code")
        found_ids = [pid for pid, _name in self.env["nme.product"].name_search("TST-1")]
        self.assertIn(self.product.id, found_ids)

    @mute_logger("odoo.sql_db")
    def test_internal_reference_unique_per_company(self):
        Product = self.env["nme.product"]
        with self.assertRaises(IntegrityError):
            Product.create({"name": "Duplicate", "default_code": "TST-1"})

        other_company = self.other_company
        Product.create(
            {
                "name": "Same code, other company",
                "default_code": "TST-1",
                "company_id": other_company.id,
            }
        )
        # Products without a code never collide.
        Product.create([{"name": "Free 1"}, {"name": "Free 2"}])

    @mute_logger("odoo.sql_db")
    def test_prices_cannot_be_negative(self):
        with self.assertRaises(IntegrityError):
            self.env["nme.product"].create({"name": "Bad", "list_price": -1})

    def test_category_complete_name_and_product_count(self):
        Category = self.env["nme.product.category"]
        rice = Category.create({"name": "Rice", "parent_id": self.categ.id})
        premium = Category.create({"name": "Premium", "parent_id": rice.id})
        self.assertEqual(premium.complete_name, "Test Staples / Rice / Premium")

        self.env["nme.product"].create(
            [
                {"name": "Premium Rice", "categ_id": premium.id},
                {"name": "Rice", "categ_id": rice.id},
            ]
        )
        self.assertEqual(premium.product_count, 1)
        self.assertEqual(rice.product_count, 2)
        # self.product is directly in the parent category.
        self.assertEqual(self.categ.product_count, 3)

    def test_category_cannot_be_recursive(self):
        child = self.env["nme.product.category"].create(
            {"name": "Child", "parent_id": self.categ.id}
        )
        with self.assertRaises(UserError):
            self.categ.parent_id = child
