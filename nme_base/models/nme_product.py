from odoo import api, fields, models


class NmeProduct(models.Model):
    """Product sold or purchased by the company.

    This module only holds the commercial definition of a product. Stock
    related fields (on hand quantity, average cost, minimum stock) are added
    by ``nme_inventory`` through ``_inherit``.
    """

    _name = "nme.product"
    _description = "Product"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "default_code, name, id"
    _check_company_auto = True
    _rec_names_search = ["name", "default_code", "barcode"]

    def _default_uom_id(self):
        return self.env.ref("nme_base.nme_uom_unit", raise_if_not_found=False)

    def _default_sale_tax_ids(self):
        return self.env.company.nme_sale_tax_id

    def _default_purchase_tax_ids(self):
        return self.env.company.nme_purchase_tax_id

    name = fields.Char(required=True, index="trigram", tracking=True)
    default_code = fields.Char(
        string="Internal Reference", index=True, copy=False, tracking=True
    )
    barcode = fields.Char(copy=False, index="btree_not_null")
    type = fields.Selection(
        [("goods", "Goods"), ("service", "Service")],
        string="Product Type",
        required=True,
        default="goods",
        tracking=True,
        help="Goods are tracked in stock, services are not.",
    )
    categ_id = fields.Many2one(
        "nme.product.category", string="Category", index=True, ondelete="restrict"
    )
    uom_id = fields.Many2one(
        "nme.uom",
        string="Unit of Measure",
        required=True,
        ondelete="restrict",
        default=lambda self: self._default_uom_id(),
    )
    currency_id = fields.Many2one("res.currency", compute="_compute_currency_id")
    list_price = fields.Monetary(string="Sales Price", tracking=True)
    purchase_price = fields.Monetary(
        tracking=True, help="Unit price proposed on new purchase orders."
    )
    # No check_company on taxes: a product shared between companies carries
    # the taxes of each company, and documents only use the taxes of their
    # own company (see _get_company_taxes).
    sale_tax_ids = fields.Many2many(
        "nme.tax",
        "nme_product_sale_tax_rel",
        "product_id",
        "tax_id",
        string="Sales Taxes",
        domain=[("type_tax_use", "=", "sale")],
        default=lambda self: self._default_sale_tax_ids(),
        help="Leave empty for goods exempted from VAT.",
    )
    purchase_tax_ids = fields.Many2many(
        "nme.tax",
        "nme_product_purchase_tax_rel",
        "product_id",
        "tax_id",
        string="Purchase Taxes",
        domain=[("type_tax_use", "=", "purchase")],
        default=lambda self: self._default_purchase_tax_ids(),
    )
    description = fields.Text(string="Internal Notes")
    company_id = fields.Many2one(
        "res.company",
        index=True,
        help="Leave empty to share the product between companies.",
    )
    active = fields.Boolean(default=True, tracking=True)

    _default_code_unique = models.UniqueIndex(
        "(default_code, company_id) NULLS NOT DISTINCT WHERE default_code IS NOT NULL",
        "The internal reference must be unique per company.",
    )
    _list_price_positive = models.Constraint(
        "CHECK(list_price >= 0)", "The sales price cannot be negative."
    )
    _purchase_price_positive = models.Constraint(
        "CHECK(purchase_price >= 0)", "The purchase price cannot be negative."
    )

    @api.depends("company_id")
    @api.depends_context("company")
    def _compute_currency_id(self):
        for product in self:
            product.currency_id = (product.company_id or self.env.company).currency_id

    @api.depends("name", "default_code")
    def _compute_display_name(self):
        for product in self:
            if product.default_code:
                product.display_name = f"[{product.default_code}] {product.name}"
            else:
                product.display_name = product.name

    def _get_company_taxes(self, tax_use, company):
        """Return the ``tax_use`` ("sale" or "purchase") taxes valid in ``company``."""
        self.ensure_one()
        taxes = self.sale_tax_ids if tax_use == "sale" else self.purchase_tax_ids
        return taxes.filtered(lambda tax: tax.company_id == company)
