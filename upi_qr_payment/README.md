# UPI QR Payment on Invoice & Quotation

Prints a **Scan & Pay** card with a dynamic UPI QR code on customer invoice and quotation / sales order PDFs.
The customer scans it with any UPI app (PhonePe, Google Pay, Paytm, BHIM, bank apps); the payee and the
amount are already filled in and they only confirm with their own UPI PIN. Works on Odoo Community and
Enterprise, depends on `sale` and `account` only.

## Install
1. Copy `upi_qr_payment` into an addons path and restart Odoo.
2. Apps → Update Apps List → install **UPI QR Payment on Invoice & Quotation**.
3. Settings → Invoicing → **UPI Scan & Pay**: enter your UPI ID (e.g. `business@okhdfcbank`) and payee name, Save.
4. Scan the *Scan to Verify* preview with your own phone: your payee name must appear. Cancel, do not pay.
5. Print an invoice or a quotation — the card is below the totals.

## Settings (per company)
| Setting | Meaning |
|---|---|
| UPI ID | The virtual payment address that receives the money. Validated as `handle@bank`. Empty = feature off. |
| Payee Name | Name shown in the customer's app. Defaults to the company name; letters, digits and spaces only. |
| QR Amount | `Grand Total` (default) or `Amount Due` — invoices only; orders always encode their total. |
| Caption | Translatable text printed under the QR. |
| UPI QR on Customer Invoices | Card on customer invoices and receipts that are not fully paid. |
| UPI QR on Quotations & Orders | Card on quotations (draft / sent) and confirmed orders. |
| Replace Odoo's Built-in Payment QR | Hides Odoo's standard bank / Indian UPI QR on invoices when the card prints. |

## Rules
* Never printed on credit notes, vendor bills, cancelled or fully paid documents, or zero amounts.
* **Any currency**: a non-INR document is converted to INR with the exchange rate at the document date
  (`invoice_date` / `date_order`); the original amount and the rate are printed under the INR figure.
  Maintain the INR rate under Accounting → Configuration → Currencies (Enterprise can update it automatically).
  If no INR rate exists the card is skipped and the settings page shows a warning.
* The QR encodes the standard `upi://pay` intent: `pa`, `pn`, `am`, `cu=INR`, `tn` ("Payment for <number>"),
  `tr` (payment reference or document number). Nothing proprietary, no gateway, no fees, no callback.
* Multi-company safe: every document reads its own company's settings.
* Works with the Indian localisation layout (`l10n_in`) but does not require it.

## Extending
`upi.qr.mixin` holds the link builder, currency conversion and QR rendering. A document model inherits it and
answers `_upi_qr_is_applicable()`, `_upi_qr_get_amount()`, `_upi_qr_get_reference()`, `_upi_qr_get_date()`,
then calls `t-call="upi_qr_payment.upi_qr_card"` with `doc` in its report.

## Tests
`--test-tags /upi_qr_payment` — 18 tests: link format and encoding, UPI ID validation, settings preview,
invoice states and amount modes, currency conversion and missing rates, sale order states, report rendering,
multi-company isolation.
