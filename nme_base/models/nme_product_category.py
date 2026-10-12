from odoo import api, fields, models


class NmeProductCategory(models.Model):
    """Hierarchical product category (for example Staples / Rice).

    ``_parent_store`` maintains ``parent_path`` so that ``child_of`` searches
    are a single indexed ``LIKE`` query instead of a recursive walk. The ORM
    also refuses loops in the hierarchy, so no extra constraint is needed.
    """

    _name = "nme.product.category"
    _description = "Product Category"
    _parent_store = True
    _rec_name = "complete_name"
    _order = "complete_name"

    name = fields.Char(required=True)
    parent_id = fields.Many2one(
        "nme.product.category",
        string="Parent Category",
        index=True,
        ondelete="restrict",
    )
    parent_path = fields.Char(index=True)
    child_ids = fields.One2many(
        "nme.product.category", "parent_id", string="Subcategories"
    )
    complete_name = fields.Char(
        compute="_compute_complete_name", recursive=True, store=True
    )
    product_count = fields.Integer(
        string="# Products",
        compute="_compute_product_count",
        help="Number of products in this category and its subcategories.",
    )

    @api.depends("name", "parent_id.complete_name")
    def _compute_complete_name(self):
        for category in self:
            if category.parent_id:
                category.complete_name = (
                    f"{category.parent_id.complete_name} / {category.name}"
                )
            else:
                category.complete_name = category.name

    def _compute_product_count(self):
        groups = self.env["nme.product"]._read_group(
            [("categ_id", "child_of", self.ids)], ["categ_id"], ["__count"]
        )
        for category in self:
            # parent_path looks like "1/4/9/": a descendant's path starts with
            # its ancestor's path, which avoids one search per category.
            category.product_count = sum(
                count
                for categ, count in groups
                if categ.parent_path.startswith(category.parent_path or "")
            )
