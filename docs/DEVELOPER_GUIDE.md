# Developer guide

How to run, test and extend Nusantara Mini ERP. Read
[ARCHITECTURE.md](ARCHITECTURE.md) first for the design.

## Development environment

### Linux or Docker

```bash
docker compose up -d
make install                 # database "nme" with demo data
make upgrade MODULES=nme_sales
make test MODULES=nme_sales  # fresh "nme_test" database
make shell                   # odoo shell on "nme"
```

### Windows, without Docker

1. Python **3.12** (Odoo 20 accepts 3.12 to 3.14, but some Windows wheels, such as
   `rl-renderPM`, only exist for 3.12).
2. `git clone --depth 1 -b 20.0 https://github.com/odoo/odoo.git`, a virtual
   environment and `pip install -r odoo/requirements.txt`.
3. `odoo.conf` with this repository in `addons_path`, and `db_template = template1`
   for PostgreSQL 18.
4. Odoo 20 stores attachments as read-only files, which `os.unlink` cannot delete on
   Windows: tests then fail when the filestore is cleaned. Start Odoo through a small
   wrapper that clears the read-only flag before deleting (retry `os.unlink` after
   `os.chmod(path, stat.S_IWRITE)`).
5. In Git Bash, set `MSYS_NO_PATHCONV=1` so that `--test-tags=/nme_sales` is not turned
   into a Windows path.

### Running tests

```bash
odoo-bin -c odoo.conf -d nme_test -i nme_reporting \
    --test-tags=/nme_base,/nme_inventory,/nme_sales,/nme_purchase,/nme_invoicing,/nme_reporting \
    --stop-after-init
```

Use a fresh database: tests only run for modules being installed or updated. The Hoot
tests of the dashboard run with the web test suite when Chrome and the
`websocket-client` package are available.

## Conventions

The code follows the official guidelines shipped with Odoo 20
(`odoo/skills/odoo-guidelines`) and the OCA layout. In short:

- One model per file, named after the model; wizards in `wizard/`, SQL views and
  report models in `report/`.
- Model body order: private attributes, default methods, fields, constraints,
  computes, onchanges/constrains, CRUD overrides, actions, business methods.
- XML ids: `<model>_view_<type>`, `<model>_action`, `<model>_menu`,
  `nme_group_<name>`; inheriting views reuse the id of the parent view.
- Translations with `self.env._("Text %s", value)`, placeholders as arguments.
- Defaults as `default=lambda self: self._default_x()` so they stay overridable.
- ASCII punctuation in code, comments and messages.
- `pre-commit run --all-files` must pass (black, isort, flake8, pylint-odoo, prettier).
  Commits follow [Conventional Commits](https://www.conventionalcommits.org/).

## Extension points

### Add a document type with the mixins

```python
class NmeQualityCheck(models.Model):
    _name = "nme.quality.check"
    _description = "Quality Check"
    _inherit = ["nme.document.mixin"]

    _state_transitions = {
        "draft": {"passed", "failed", "cancel"},
        "failed": {"draft"},
        "cancel": {"draft"},
    }

    state = fields.Selection(
        [("draft", "Draft"), ("passed", "Passed"), ("failed", "Failed"),
         ("cancel", "Cancelled")],
        required=True, readonly=True, copy=False, tracking=True, default="draft",
    )

    def action_pass(self):
        self._set_state("passed")
```

Add an `ir.sequence` with code `nme.quality.check` and the document is numbered,
tracked in the chatter, cancellable with a reason (`action_open_cancel_wizard`) and
protected against deletion once confirmed.

### Change the proposed price of order lines

```python
class NmeSaleOrderLine(models.Model):
    _inherit = "nme.sale.order.line"

    def _get_product_price(self):
        price = super()._get_product_price()
        if self.order_id.partner_id.category_id.filtered(lambda c: c.name == "Grosir"):
            return price * 0.95
        return price
```

`_get_product_taxes` works the same way for taxes.

### Add information to generated documents

Deliveries, receipts, invoices and bills are built by `_prepare_*_values` methods that
return the values to create:

| Method                            | Model                |
| --------------------------------- | -------------------- |
| `_prepare_delivery_values(lines)` | `nme.sale.order`     |
| `_prepare_receipt_values(lines)`  | `nme.purchase.order` |
| `_prepare_invoice_values(lines)`  | `nme.sale.order`     |
| `_prepare_bill_values(lines)`     | `nme.purchase.order` |
| `_prepare_return_values()`        | `nme.picking`        |

```python
def _prepare_invoice_values(self, lines):
    values = super()._prepare_invoice_values(lines)
    values["note"] = self.note
    return values
```

### Refine the credit exposure

```python
class ResPartner(models.Model):
    _inherit = "res.partner"

    def _get_credit_exposure(self):
        exposure = super()._get_credit_exposure()
        return exposure + self._get_unpaid_cheques_amount()
```

### Add a state to an existing document

Extend the selection with `selection_add` and complete `_state_transitions`:

```python
from odoo import fields, models

from odoo.addons.nme_sales.models.nme_sale_order import NmeSaleOrder as SaleOrderBase


class NmeSaleOrder(models.Model):
    _inherit = "nme.sale.order"

    state = fields.Selection(
        selection_add=[("locked", "Locked")], ondelete={"locked": "set default"}
    )
    # Build a new dictionary from the parent's instead of mutating it.
    _state_transitions = {
        **SaleOrderBase._state_transitions,
        "sale": {"cancel", "locked"},
        "locked": {"sale"},
    }

    def action_lock(self):
        self._set_state("locked")
```

### Add a dashboard figure

Override one of the `_get_*_kpis` methods of `nme.dashboard` and append a dictionary
built with `self._kpi(key, label, value, model, domain, kind="integer")`. The OWL
component renders any number of cards.

## Security checklist for new models

1. A permission row per group in `security/ir.access.csv` (default is deny).
2. A group-less restriction `[('company_id', 'in', company_ids)]` for company records.
3. For wizards: a permission row and a restriction `[('create_uid', '=', user.id)]`.
4. Prefer the `access` operator to give access through a parent document over `sudo()`.
5. A test with a user holding only the minimum groups.

## Translations

Source strings are in English. To update the Indonesian translation after changing
strings:

```bash
odoo-bin i18n export -c odoo.conf -d nme nme_sales            # i18n/nme_sales.pot
msgmerge --update nme_sales/i18n/id.po nme_sales/i18n/nme_sales.pot
```

then translate the new entries in `id.po` and update the module.

## Release checklist

1. `pre-commit run --all-files`
2. Full test run on a fresh database, coverage above 80%.
3. Bump `version` in the changed manifests (`20.0.x.y.z`).
4. Move the _Unreleased_ entries of `CHANGELOG.md` under the new version.
