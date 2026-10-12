from odoo import Command

from odoo.addons.base.tests.common import BaseCommon


class NmeBaseCommon(BaseCommon):
    """Common fixtures of Nusantara ERP tests.

    Fixtures are created in ``setUpClass`` by the superuser. Test methods then
    run as ``_test_user``, a regular internal user holding only the groups
    listed in ``_test_user_groups`` (``BaseCommon`` switches the environment
    before each test). Tests create their own data and never rely on demo
    records, so they also run on a database without demo data.
    """

    _test_user_groups = (
        "base.group_user",
        "base.group_partner_manager",
        "nme_base.nme_group_master_data_manager",
    )

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.uom_unit = cls.env.ref("nme_base.nme_uom_unit")
        Tax = cls.env["nme.tax"]
        cls.tax_sale = Tax.create(
            {
                "name": "Test VAT 11%",
                "amount": 11.0,
                "type_tax_use": "sale",
                "company_id": cls.company.id,
            }
        )
        cls.tax_purchase = Tax.create(
            {
                "name": "Test VAT 11% (Purchase)",
                "amount": 11.0,
                "type_tax_use": "purchase",
                "company_id": cls.company.id,
            }
        )
        cls.company.write(
            {
                "nme_sale_tax_id": cls.tax_sale.id,
                "nme_purchase_tax_id": cls.tax_purchase.id,
            }
        )
        cls.categ = cls.env["nme.product.category"].create({"name": "Test Staples"})
        cls.product = cls.env["nme.product"].create(
            {
                "name": "Test Rice",
                "default_code": "TST-1",
                "categ_id": cls.categ.id,
                "list_price": 100000.0,
                "purchase_price": 80000.0,
            }
        )
        # A second company the test user may also work in.
        cls.other_company = cls.env["res.company"].create({"name": "Second Branch"})
        cls._test_user.company_ids = [Command.link(cls.other_company.id)]

    @classmethod
    def setup_main_company(cls, currency_code="IDR"):
        return super().setup_main_company(currency_code=currency_code)
