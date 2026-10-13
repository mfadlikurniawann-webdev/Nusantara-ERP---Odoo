import operator
from collections import defaultdict

from odoo import api, fields, models
from odoo.exceptions import ValidationError
from odoo.fields import Domain

PY_OPERATORS = {
    "<": operator.lt,
    ">": operator.gt,
    "<=": operator.le,
    ">=": operator.ge,
    "=": operator.eq,
    "!=": operator.ne,
    "in": lambda value, container: value in container,
    "not in": lambda value, container: value not in container,
}


class NmeProduct(models.Model):
    """Stock information of products, computed from the stock move ledger."""

    _inherit = "nme.product"

    qty_available = fields.Float(
        string="On Hand",
        digits="Nusantara Quantity",
        compute="_compute_stock_info",
        search="_search_qty_available",
        help="Done moves into internal locations minus done moves out of them. "
        "Use the warehouse_id or location_id context key to restrict it.",
    )
    # company_dependent fields cannot be Monetary (like standard_price in Odoo).
    avg_cost = fields.Float(
        string="Average Cost",
        digits=(16, 2),
        company_dependent=True,
        readonly=True,
        help="Weighted average cost of the stock, updated by every receipt.",
    )
    stock_value = fields.Monetary(compute="_compute_stock_info")
    min_qty = fields.Float(
        string="Minimum Stock",
        digits="Nusantara Quantity",
        company_dependent=True,
        help="A scheduled action warns the inventory managers below this level.",
    )
    is_below_min = fields.Boolean(
        string="Below Minimum",
        compute="_compute_stock_info",
        search="_search_is_below_min",
    )
    stock_move_ids = fields.One2many("nme.stock.move", "product_id")

    @api.depends("type", "avg_cost", "min_qty")
    @api.depends_context("company", "warehouse_id", "location_id")
    def _compute_stock_info(self):
        quantities = self._origin._get_quantities(self._get_stock_locations())
        for product in self:
            qty = quantities[product._origin.id] if product.type == "goods" else 0.0
            product.qty_available = qty
            product.stock_value = qty * product.avg_cost
            product.is_below_min = (
                product.type == "goods"
                and product.min_qty > 0
                and qty < product.min_qty
            )

    def _search_qty_available(self, operator, value):
        compare = PY_OPERATORS.get(operator)
        if not compare:
            return NotImplemented
        products = self.with_context(active_test=False).search([("type", "=", "goods")])
        return Domain(
            "id", "in", [p.id for p in products if compare(p.qty_available, value)]
        )

    def _search_is_below_min(self, operator, value):
        if operator not in ("in", "not in", "=", "!="):
            return NotImplemented
        products = self.search([("type", "=", "goods"), ("min_qty", ">", 0)])
        below = products.filtered("is_below_min")
        wanted = value if operator in ("in", "not in") else [value]
        positive = (True in wanted) == (operator in ("in", "="))
        return Domain("id", "in" if positive else "not in", below.ids)

    @api.constrains("type")
    def _check_type_without_moves(self):
        for product in self:
            if product.type == "service" and product.stock_move_ids:
                raise ValidationError(
                    self.env._(
                        "%s already has stock moves and cannot become a service.",
                        product.display_name,
                    )
                )

    def _get_stock_locations(self):
        """Internal locations selected by the context, else the company's."""
        context = self.env.context
        Location = self.env["nme.location"]
        if context.get("location_id"):
            return Location.browse(context["location_id"])
        domain = Domain("usage", "=", "internal") & Domain(
            "company_id", "=", self.env.company.id
        )
        if context.get("warehouse_id"):
            domain &= Domain("warehouse_id", "=", context["warehouse_id"])
        return Location.search(domain)

    def _get_quantities(self, locations):
        """Return ``{product_id: quantity}`` in ``locations`` from done moves.

        Moves between two of the given locations are ignored: they do not
        change the total quantity of the group.
        """
        quantities = defaultdict(float)
        if not self.ids or not locations:
            return quantities
        Move = self.env["nme.stock.move"]
        done = Domain("product_id", "in", self.ids) & Domain("state", "=", "done")
        inside = Domain("location_dest_id", "in", locations.ids) & Domain(
            "location_id", "not in", locations.ids
        )
        outside = Domain("location_id", "in", locations.ids) & Domain(
            "location_dest_id", "not in", locations.ids
        )
        for product, qty in Move._read_group(
            done & inside, ["product_id"], ["quantity:sum"]
        ):
            quantities[product.id] += qty
        for product, qty in Move._read_group(
            done & outside, ["product_id"], ["quantity:sum"]
        ):
            quantities[product.id] -= qty
        return quantities

    def action_view_stock_moves(self):
        self.ensure_one()
        return {
            "name": self.env._("Stock Moves"),
            "type": "ir.actions.act_window",
            "res_model": "nme.stock.move",
            "view_mode": "list,pivot",
            "domain": [("product_id", "=", self.id), ("state", "=", "done")],
            "context": {"search_default_group_by_location_dest": 0},
        }

    @api.model
    def _cron_check_minimum_stock(self):
        """Schedule a "Low Stock" activity for the inventory managers."""
        activity_type = self.env.ref("nme_inventory.mail_activity_type_low_stock")
        managers_group = self.env.ref("nme_inventory.nme_group_inventory_manager")
        # Only companies that can hold stock, i.e. with an active warehouse.
        warehouse_groups = self.env["nme.warehouse"]._read_group(
            [("active", "=", True)], ["company_id"]
        )
        for (company,) in warehouse_groups:
            products = self.with_company(company).search(
                [("type", "=", "goods"), ("min_qty", ">", 0)]
            )
            low_products = products.filtered("is_below_min")
            managers = managers_group.user_ids.filtered(
                lambda user, company=company: user.active
                and not user.share
                and company in user.company_ids
            )
            if not low_products or not managers:
                continue
            existing = {
                (activity.res_id, activity.user_id.id)
                for activity in self.env["mail.activity"].search(
                    [
                        ("res_model", "=", self._name),
                        ("res_id", "in", low_products.ids),
                        ("activity_type_id", "=", activity_type.id),
                    ]
                )
            }
            for product in low_products:
                for user in managers:
                    if (product.id, user.id) in existing:
                        continue
                    product.activity_schedule(
                        "nme_inventory.mail_activity_type_low_stock",
                        user_id=user.id,
                        note=self.env._(
                            "%(qty)s %(unit)s left, minimum %(min)s.",
                            qty=product.qty_available,
                            unit=product.uom_id.code,
                            min=product.min_qty,
                        ),
                    )
