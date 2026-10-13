=========================
Nusantara ERP - Sales
=========================

Sales flow of Nusantara Mini ERP: quotation, sales order, delivery and
customer credit limits.

**Table of contents**

.. contents::
   :local:

Features
========

* Quotations with per-line discounts and taxes, sent by email with the PDF
  attached (sending marks the quotation as sent).
* Strict state machine: Quotation, Quotation Sent, Sales Order, Cancelled.
  Confirmed lines are locked; cancelling requires a reason.
* Confirming an order creates the delivery of the goods (services are not
  delivered). The delivered quantity and the delivery status are computed
  from the stock ledger, returns included.
* **Credit limit** per customer and company with three policies:

  * *No Limit*;
  * *Warn*: confirming above the limit is allowed and logged in the chatter;
  * *Block*: only a sales manager can confirm above the limit.

  The credit used is computed by ``res.partner._get_credit_exposure``; this
  module counts confirmed orders and ``nme_invoicing`` refines it with
  unpaid invoices.
* Kanban by status, calendar of promised delivery dates, pivot and graph
  views, mass confirmation from the list and a printable quotation/order.

Configuration
=============

*Nusantara ERP > Configuration > Settings*: default quotation validity.
Credit limits are set by sales managers on the customer form
(*Sales & Purchase* tab).

Security
========

* *Sales / User: Own Documents Only*: their own (or unassigned) orders;
  order lines follow their order through the ``access`` domain operator of
  ``ir.access``. They also prepare deliveries (outgoing transfers).
* *Sales / Manager*: every order, credit limits and limit overrides.
* Inventory users can read sales orders to prepare deliveries.

Credits
=======

Author
------

* M. Fadli Kurniawan

License
-------

LGPL-3
