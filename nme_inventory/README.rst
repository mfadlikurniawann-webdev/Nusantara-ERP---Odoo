=============================
Nusantara ERP - Inventory
=============================

Stock management of Nusantara Mini ERP: warehouses, transfers and a stock
move ledger valued with the average cost method.

**Table of contents**

.. contents::
   :local:

Features
========

* Warehouses with an automatically created stock location; every new
  company gets its own warehouse.
* Transfers (``nme.picking``) of three types: receipts, deliveries and
  internal transfers between warehouses, with kanban, calendar and a
  printable delivery slip (Surat Jalan).
* **Stock move ledger**: the quantity on hand is never stored on the
  product; it is computed from done moves. Done moves are immutable and
  negative stock is refused.
* **Average cost (AVCO)** per company, updated by every receipt; deliveries
  and transfers are valued at the current average cost.
* Full returns of done transfers (returned deliveries come back at their
  original cost).
* Stock adjustments (stock opname) with a mandatory reason, validated by an
  inventory manager, plus a quick "Update Quantity" wizard on products.
* Minimum stock per product and company, with a daily scheduled action
  creating "Low Stock" activities for the inventory managers.

Design notes
============

Stock follows a double-entry logic: every move goes from one location to
another. Internal locations hold stock; virtual locations (Vendors,
Customers, Inventory Adjustment) are the counterparts. Quantities are
computed with grouped queries on the ledger (``_read_group``), filtered by
the ``warehouse_id`` or ``location_id`` context keys.

Security
========

* *Inventory / User*: creates and validates transfers, records stock counts.
* *Inventory / Manager*: validates stock adjustments, manages warehouses,
  locations and reasons.
* Every internal user can read the ledger; records are filtered by company.

Credits
=======

Author
------

* M. Fadli Kurniawan

License
-------

LGPL-3
