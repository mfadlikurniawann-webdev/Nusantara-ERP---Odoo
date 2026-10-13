=============================
Nusantara ERP - Invoicing
=============================

Customer invoices, vendor bills, partial payments, overdue follow-up and
aging reports of Nusantara Mini ERP.

**Table of contents**

.. contents::
   :local:

Features
========

* Customer invoices and vendor bills created from sales and purchase
  orders: goods are invoiced on the **delivered / received** quantity,
  services on the ordered quantity. Orders show the invoiced quantity and
  their invoicing status.
* **Numbering on posting**: drafts have no number; the ``no_gap`` sequences
  ``INV/`` and ``BILL/`` are only consumed when an invoice is posted, and a
  numbered invoice can be cancelled but never deleted.
* Due date from the payment terms, taxes per line (VAT 11% by default).
* **Partial payments** through the *Register Payment* wizard; payment state
  ``not_paid`` / ``partial`` / ``paid`` and amount due computed from the
  posted payments. An invoice can never be paid more than its total.
* Daily scheduled action flagging overdue invoices and creating an
  "Overdue Invoice" activity for the salesperson.
* **Aging report** (SQL view) of receivables and payables by bucket
  (not due, 1-30, 31-60, 61-90, over 90 days), always computed on the
  current date.
* The customer credit exposure of ``nme_sales`` is extended: the invoiced
  part of the orders is replaced by the amount still due on invoices.
* Printable invoice, email sending, mass posting from the list.

Security
========

* *Invoicing / User*: creates and posts invoices, registers payments.
* *Invoicing / Manager*: cancels or resets posted invoices, cancels
  payments.
* Salespeople and buyers can read the invoices of the orders they can read
  (``access`` domain operator).

Credits
=======

Author
------

* M. Fadli Kurniawan

License
-------

LGPL-3
