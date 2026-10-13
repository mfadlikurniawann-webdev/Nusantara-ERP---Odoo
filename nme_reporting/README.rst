=============================
Nusantara ERP - Reporting
=============================

Dashboard and analysis reports of Nusantara Mini ERP.

**Table of contents**

.. contents::
   :local:

Features
========

* **Dashboard** (OWL client action), the landing page of the Nusantara ERP
  app: sales of the month, orders to deliver, receivables, overdue invoices,
  payables, products below minimum, purchases to approve, and a chart of
  the sales of the last six months. Each card opens the matching records.
  Figures are computed in one call with the rights of the user: cards about
  documents the user cannot read are not shown.
* **Sales analysis** (SQL view) per order line with the margin of the
  delivered goods: revenue of the delivered quantity minus the value of the
  delivery moves at average cost, customer returns included.
* **Purchase analysis** with the average net unit price per vendor/product.
* **Stock by warehouse**: quantity per internal location from the stock
  ledger, valued at the average cost of the location's company.
* **Export to Excel** (xlsxwriter) of the stock, receivable/payable aging
  and sales by product, and a **PDF aging report** by partner and bucket
  (custom ``report.*`` model).

Technical notes
===============

* The dashboard is an OWL 3 component (``proxy`` state, ``useChart`` hook
  with the Chart.js bundle of the web client) with a Hoot unit test in
  ``static/tests``, run by the web test suite when Chrome is available.
* SQL views declare ``_depends`` so that pending ORM writes are flushed
  before they are read.

Security
========

Each report follows the groups of its source documents: sales users see the
analysis of their own orders, purchase users the purchase analysis,
inventory users the stock report; all of them are filtered by company.

Credits
=======

Author
------

* M. Fadli Kurniawan

License
-------

LGPL-3
