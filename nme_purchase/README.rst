============================
Nusantara ERP - Purchase
============================

Purchase flow of Nusantara Mini ERP: request for quotation, purchase order
with tiered approval and receipt of the goods.

**Table of contents**

.. contents::
   :local:

Features
========

* Requests for quotation sent by email with the PDF attached (sending marks
  the RFQ as sent), vendor reference and expected arrival date.
* **Tiered approval**: an order whose total (taxes included) reaches the
  company approval amount, confirmed by a purchase user, goes to
  *To Approve* and every purchase manager of the company gets a
  "Purchase Approval" activity. Managers approve or reject it; orders they
  confirm themselves skip the approval.
* Confirmed orders create the receipt of the goods. The received quantity
  and receipt status come from the stock ledger (returns to the vendor
  included), and receiving updates the average cost with the **net** price
  of the line (after discount, without taxes).
* Locked lines once waiting for approval or confirmed; cancellation with a
  reason, refused while goods are received and not returned.
* Kanban by status, calendar of expected arrivals, pivot and graph views,
  vendor smart button and a printable RFQ / purchase order.

Configuration
=============

*Nusantara ERP > Configuration > Settings > Purchase Approval*: approval
amount per company (default Rp 50.000.000, 0 disables the approval).

Security
========

* *Purchase / User*: every purchase order of their companies, and the
  receipts (incoming transfers).
* *Purchase / Manager*: approves or rejects orders above the threshold.
* Inventory users can read purchase orders to receive the goods.

Credits
=======

Author
------

* M. Fadli Kurniawan

License
-------

LGPL-3
