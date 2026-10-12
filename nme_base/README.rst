=========================
Nusantara ERP - Base
=========================

Foundation of Nusantara Mini ERP, a small ERP for Indonesian distributors
built on Odoo 20 Community.

**Table of contents**

.. contents::
   :local:

Features
========

* Master data shared by every module: products, hierarchical product
  categories, units of measure, taxes and payment terms.
* Customer and vendor flags and per-company payment terms on contacts. The
  NPWP (tax number) is Odoo's standard Tax ID field, validated by Odoo.
* Company settings: default sales/purchase tax and default payment terms.
* Abstract mixins reused by all business documents:

  * ``nme.document.mixin``: sequence numbering, strict state machine
    (``_state_transitions`` + ``_set_state``), cancellation with a reason,
    chatter and protection against deleting confirmed documents.
  * ``nme.trade.document.mixin``: partner, payment terms and computed totals.
  * ``nme.trade.line.mixin``: product, quantity, price, discount, taxes and
    computed amounts.

* A generic "Cancel with reason" wizard (``nme.document.cancel``).

Configuration
=============

Go to *Nusantara ERP > Configuration > Settings* to choose the default taxes
and payment terms of the company. The module creates a "VAT 11%" sales tax
and purchase tax for the main company. Leave the tax fields of a product
empty for goods exempted from VAT.

Security
========

* Every internal user can read master data.
* *Nusantara ERP / Master Data: Manager* creates and edits it.
* Products, taxes and payment terms are filtered by the user's allowed
  companies (shared records have no company).

Credits
=======

Author
------

* M. Fadli Kurniawan

License
-------

LGPL-3
