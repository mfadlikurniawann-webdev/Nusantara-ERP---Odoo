from odoo.exceptions import AccessError, UserError
from odoo.tests import new_test_user, tagged
from odoo.tools import mute_logger

from .common import NmeBaseCommon


@tagged("post_install", "-at_install")
class TestNmeBaseSecurity(NmeBaseCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user_internal = new_test_user(
            cls.env, login="nme_internal", groups="base.group_user"
        )
        cls.user_manager = new_test_user(
            cls.env,
            login="nme_md_manager",
            groups="nme_base.nme_group_master_data_manager",
        )
        cls.other_product = cls.env["nme.product"].create(
            {"name": "Other Company Rice", "company_id": cls.other_company.id}
        )

    @mute_logger("odoo.addons.base.models.ir_access")
    def test_internal_user_reads_but_cannot_write_master_data(self):
        Product = self.env["nme.product"].with_user(self.user_internal)
        self.assertEqual(Product.search([("id", "=", self.product.id)]), self.product)
        with self.assertRaises(AccessError):
            Product.create({"name": "Forbidden"})
        with self.assertRaises(AccessError):
            self.product.with_user(self.user_internal).list_price = 1
        with self.assertRaises(AccessError):
            self.env["nme.tax"].with_user(self.user_internal).create(
                {"name": "Forbidden", "amount": 1}
            )

    def test_master_data_manager_manages_master_data(self):
        product = (
            self.env["nme.product"]
            .with_user(self.user_manager)
            .create({"name": "Allowed", "categ_id": self.categ.id})
        )
        product.list_price = 5000
        self.assertEqual(product.sale_tax_ids, self.tax_sale)

    def test_records_of_other_companies_are_hidden(self):
        Product = self.env["nme.product"].with_user(self.user_manager)
        visible = Product.search(
            [("id", "in", (self.product | self.other_product).ids)]
        )
        # Shared product (no company) is visible, the other company's is not.
        self.assertEqual(visible, self.product)

    def test_cancel_wizard_only_accepts_nusantara_documents(self):
        wizard = self.env["nme.document.cancel"].create(
            {
                "res_model": "res.partner",
                "res_ids": self.env.user.partner_id.ids,
                "reason": "Not a document",
            }
        )
        with self.assertRaises(UserError):
            wizard.action_confirm()
