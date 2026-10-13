# Changelog

All notable changes to this project are documented in this file. The format is based
on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project uses
[Conventional Commits](https://www.conventionalcommits.org/).

## [Unreleased]

### Added

- Repository tooling: Docker Compose (Odoo 20 + PostgreSQL 16), Makefile, pre-commit
  (black, isort, flake8, pylint-odoo, prettier) and GitHub Actions CI with coverage.
- `nme_base`: products, product categories, units of measure, taxes, payment terms,
  customer/vendor flags, company settings, document mixins (numbering, state machine,
  cancellation with reason, totals) and a generic cancellation wizard.
- `nme_inventory`: warehouses and locations, receipts/deliveries/internal transfers,
  immutable stock move ledger with average cost (AVCO) per company, full returns,
  stock adjustments validated by managers, quick quantity update wizard, minimum stock
  scheduled action with "Low Stock" activities and a printable delivery slip.
- `nme_sales`: quotations and sales orders with strict states, email sending with PDF,
  automatic deliveries, delivered quantity from the ledger (returns included),
  per-customer credit limits (warn/block) and own-documents access for salespeople.
- `nme_purchase`: RFQs and purchase orders, tiered approval above a company amount
  with manager activities, automatic receipts valued at the net purchase price,
  received quantity from the ledger and vendor returns.
- `nme_invoicing`: customer invoices and vendor bills from orders (delivered/received
  quantities), gapless numbering on posting, partial payments, overdue scheduled
  action, receivable/payable aging report and credit exposure based on open invoices.
- `nme_reporting`: OWL 3 dashboard with KPIs and a sales chart (Hoot tests), sales
  analysis with margin of delivered goods, purchase analysis, stock by warehouse,
  Excel export and a PDF aging report.
