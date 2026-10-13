# Nusantara Mini ERP

[![CI](https://github.com/mfadlikurniawann-webdev/Nusantara-ERP---Odoo/actions/workflows/ci.yml/badge.svg)](https://github.com/mfadlikurniawann-webdev/Nusantara-ERP---Odoo/actions/workflows/ci.yml)
![Odoo 20](https://img.shields.io/badge/Odoo-20.0%20Community-714B67)
![License: LGPL-3](https://img.shields.io/badge/license-LGPL--3-blue)

A compact, multi-module ERP for an Indonesian staples distributor (UMKM), built on
**Odoo 20 Community** as a portfolio project.

> Work in progress. Full documentation (architecture, ERD, business flows) is added
> in a later phase.

## Modules

| Module          | Purpose                                                              | Status  |
| --------------- | -------------------------------------------------------------------- | ------- |
| `nme_base`      | Master data, shared document mixins, taxes, payment terms, settings  | Done    |
| `nme_inventory` | Warehouses, stock moves ledger, average cost, adjustments, transfers | Done    |
| `nme_sales`     | Quotation, sales order, delivery, credit limit                       | Done    |
| `nme_purchase`  | RFQ, purchase order, receipt, approval                               | Planned |
| `nme_invoicing` | Customer invoices, vendor bills, payments, aging                     | Planned |
| `nme_reporting` | Analysis reports, dashboard, Excel export                            | Planned |

## Quick start (Docker)

```bash
docker compose up -d
make install          # installs all modules with demo data in database "nme"
```

Then open http://localhost:8069 (set `ODOO_PORT` to use another port).

## Running the tests

```bash
make test             # fresh database, installs the modules, runs their tests
make coverage         # same, with a coverage report
make lint             # pre-commit: black, isort, flake8, pylint-odoo, prettier
```

## License

[LGPL-3](LICENSE)
