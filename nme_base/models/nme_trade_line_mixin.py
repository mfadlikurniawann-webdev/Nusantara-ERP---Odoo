from odoo import api, fields, models
from odoo.exceptions import ValidationError


class NmeTradeLineMixin(models.AbstractModel):
    """Priced line of a trade document: product, quantity, price, discount, taxes.

    Description, unit price and taxes are stored computed fields that stay
    editable (``readonly=False``): they are proposed from the product and the
    user can still change them. Concrete lines provide the product defaults by
    overriding ``_get_product_price`` and ``_get_product_taxes``, and redefine
    ``company_id`` and ``currency_id`` as related fields of their document.
    """

    _name = "nme.trade.line.mixin"
    _description = "Nusantara ERP Trade Document Line"
    _check_company_auto = True
    _order = "sequence, id"

    sequence = fields.Integer(default=10)
    company_id = fields.Many2one("res.company", index=True)
    currency_id = fields.Many2one("res.currency")
    product_id = fields.Many2one(
        "nme.product",
        required=True,
        index=True,
        ondelete="restrict",
        check_company=True,
    )
    name = fields.Text(
        string="Description",
        compute="_compute_name",
        store=True,
        readonly=False,
        required=True,
    )
    quantity = fields.Float(digits="Nusantara Quantity", required=True, default=1.0)
    uom_id = fields.Many2one(related="product_id.uom_id", string="Unit")
    price_unit = fields.Monetary(
        string="Unit Price",
        compute="_compute_price_unit",
        store=True,
        readonly=False,
    )
    discount = fields.Float(string="Discount (%)", digits=(5, 2), default=0.0)
    tax_ids = fields.Many2many(
        "nme.tax",
        string="Taxes",
        compute="_compute_tax_ids",
        store=True,
        readonly=False,
        check_company=True,
    )
    price_subtotal = fields.Monetary(
        string="Subtotal", compute="_compute_amounts", store=True
    )
    price_tax = fields.Monetary(string="Tax", compute="_compute_amounts", store=True)
    price_total = fields.Monetary(
        string="Total", compute="_compute_amounts", store=True
    )

    @api.depends("product_id")
    def _compute_name(self):
        for line in self:
            line.name = line.product_id.display_name

    @api.depends("product_id")
    def _compute_price_unit(self):
        for line in self:
            line.price_unit = line._get_product_price()

    @api.depends("product_id")
    def _compute_tax_ids(self):
        for line in self:
            line.tax_ids = line._get_product_taxes()

    @api.depends("quantity", "price_unit", "discount", "tax_ids.amount", "currency_id")
    def _compute_amounts(self):
        for line in self:
            currency = line.currency_id or self.env.company.currency_id
            subtotal = currency.round(
                line.quantity * line.price_unit * (1.0 - line.discount / 100.0)
            )
            tax = line.tax_ids._get_tax_amount(subtotal, currency)
            line.price_subtotal = subtotal
            line.price_tax = tax
            line.price_total = subtotal + tax

    @api.constrains("quantity", "price_unit", "discount")
    def _check_line_values(self):
        for line in self:
            if line.quantity <= 0:
                raise ValidationError(
                    self.env._("The quantity of %s must be positive.", line.name)
                )
            if line.price_unit < 0:
                raise ValidationError(
                    self.env._("The unit price of %s cannot be negative.", line.name)
                )
            if not 0 <= line.discount <= 100:
                raise ValidationError(
                    self.env._(
                        "The discount of %s must be between 0 and 100%%.", line.name
                    )
                )

    def _get_product_price(self):
        """Unit price proposed for the line's product."""
        return 0.0

    def _get_product_taxes(self):
        """Taxes proposed for the line's product."""
        return self.env["nme.tax"]
