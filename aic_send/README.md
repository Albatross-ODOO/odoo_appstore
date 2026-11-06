# Core Share on WhatsApp (Odoo 20)

A **WhatsApp** button in the chatter of every record (next to *Send message* and *Log note*). It opens a short
sheet with:
- the contact's number in international form (E.164 when `phone_validation` is installed, otherwise the
  country's calling code is added to a local number);
- a message written for the record: quotation (amount, validity), order, customer invoice (amount, due date),
  vendor bill, purchase order (expected delivery), or any other record;
- for records with a customer portal (quotations, orders, invoices, purchase orders, tickets, tasks…), a secure
  link (`_get_share_url`) the customer can open without logging in.

**Open WhatsApp** opens WhatsApp Web or the app with the message ready (`wa.me`); the user presses Send there. The
share is logged on the record as a note, a draft quotation is marked as sent (`action_quotation_sent`), and the
sheet closes so the page refreshes. No WhatsApp Business account or API is involved, so it works on Community and
Enterprise. A contact person of a company is greeted by first name; companies and individual customers by full
name (Odoo 20 derives `is_company` from the VAT number, so it is not used).

Turn it off in *Settings → Backend theme → Share on WhatsApp* (the flag reaches the web client through
`session_info.aic_whatsapp_share`).

Tests (`tests/test_share.py`): contact defaults and URL, quotation message with link and the sent state, the
greeting rule, number validation, and the setting flag in the page.
