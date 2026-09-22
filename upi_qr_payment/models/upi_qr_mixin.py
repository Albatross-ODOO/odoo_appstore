import base64
import logging
import re
import urllib.parse

from odoo import _, api, fields, models
from odoo.tools import format_amount, format_date

_logger = logging.getLogger(__name__)

# handle@psp, e.g. business@okhdfcbank, 9876543210@ybl
UPI_ID_RE = re.compile(r'^[A-Za-z0-9._-]{2,}@[A-Za-z][A-Za-z0-9]+$')


class UpiQrMixin(models.AbstractModel):
    """Everything needed to put a UPI Scan & Pay card on a document.

    A document model inherits this mixin and answers four questions through the
    hooks below: is the card applicable, which amount, which reference, which
    date. The mixin builds the ``upi://pay`` link, converts the amount to INR
    with Odoo's exchange rates and renders the QR image.
    """
    _name = 'upi.qr.mixin'
    _description = 'UPI QR Code'

    upi_qr_uri = fields.Char(string="UPI Payment Link", compute='_compute_upi_qr')
    upi_qr_image = fields.Binary(string="UPI QR Code", compute='_compute_upi_qr')
    upi_qr_amount = fields.Float(string="UPI Amount (INR)", compute='_compute_upi_qr', digits=(16, 2))
    upi_qr_fx_note = fields.Char(string="UPI Conversion Note", compute='_compute_upi_qr')

    # ------------------------------------------------------------------
    # Hooks — override on the document model
    # ------------------------------------------------------------------
    def _upi_qr_is_applicable(self):
        self.ensure_one()
        return False

    def _upi_qr_get_amount(self):
        """Amount to pay, in the document currency."""
        self.ensure_one()
        return 0.0

    def _upi_qr_get_amount_label(self):
        self.ensure_one()
        return _("Amount")

    def _upi_qr_get_currency(self):
        self.ensure_one()
        return self.currency_id

    def _upi_qr_get_company(self):
        self.ensure_one()
        return self.company_id

    def _upi_qr_get_reference(self):
        """Document number, used as transaction reference and in the note."""
        self.ensure_one()
        return self.display_name or ''

    def _upi_qr_get_date(self):
        """Date of the exchange rate used for a non-INR document."""
        self.ensure_one()
        return fields.Date.context_today(self)

    # ------------------------------------------------------------------
    # Helpers — also used by the settings preview
    # ------------------------------------------------------------------
    @api.model
    def _upi_qr_is_valid_id(self, upi_id):
        return bool(upi_id and UPI_ID_RE.match(upi_id.strip()))

    @api.model
    def _upi_qr_clean_payee(self, name):
        """UPI apps only accept letters, digits and spaces in the payee name."""
        cleaned = re.sub(r'[^A-Za-z0-9 ]+', ' ', name or '')
        return re.sub(r'\s+', ' ', cleaned).strip()[:99]

    @api.model
    def _upi_qr_build_uri(self, upi_id, payee_name, amount, reference=None, note=None):
        params = [
            ('pa', (upi_id or '').strip().lower()),
            ('pn', self._upi_qr_clean_payee(payee_name) or 'Payee'),
            ('am', '%.2f' % amount),
            ('cu', 'INR'),
        ]
        if note:
            params.append(('tn', re.sub(r'[^A-Za-z0-9 /_.-]+', ' ', note).strip()[:80]))
        if reference:
            params.append(('tr', re.sub(r'[^A-Za-z0-9/_.-]+', '', reference)[:35]))
        return 'upi://pay?' + urllib.parse.urlencode(params, quote_via=urllib.parse.quote)

    @api.model
    def _upi_qr_render(self, uri, size=600):
        """PNG QR as base64. Error-correction M and a 4-module quiet zone so a printed
        card scans reliably (``quiet=False`` is what makes Odoo's helper keep the border)."""
        png = self.env['ir.actions.report'].barcode(
            'QR', uri, width=size, height=size, barLevel='M', quiet=False, barBorder=4)
        return base64.b64encode(png)

    @api.model
    def _upi_qr_get_inr(self):
        return self.env['res.currency'].with_context(active_test=False).search([('name', '=', 'INR')], limit=1)

    @api.model
    def _upi_qr_has_rate(self, currency, company, date):
        """Odoo silently uses 1.0 for a currency without rates; refuse that."""
        if currency == company.currency_id:
            return True
        root = company.root_id if 'root_id' in company._fields else company
        return bool(self.env['res.currency.rate'].sudo().search_count([
            ('currency_id', '=', currency.id),
            ('company_id', 'in', (root.id, False)),
            ('name', '<=', date),
        ]))

    @api.model
    def _upi_qr_convert(self, amount, currency, company, date):
        """Return ``(inr_amount, fx_note)``; ``(0.0, False)`` when no rate is available."""
        inr = self._upi_qr_get_inr()
        if not inr:
            return 0.0, False
        if currency == inr:
            return currency.round(amount), False
        if not (self._upi_qr_has_rate(currency, company, date) and self._upi_qr_has_rate(inr, company, date)):
            return 0.0, False
        inr_amount = currency._convert(amount, inr, company, date)
        if inr_amount <= 0:
            return 0.0, False
        rate = inr_amount / amount
        note = _("%(original)s converted at 1 %(currency)s = %(rate)s on %(date)s",
                 original=format_amount(self.env, amount, currency),
                 currency=currency.name,
                 rate=format_amount(self.env, rate, inr),
                 date=format_date(self.env, date))
        return inr_amount, note

    # ------------------------------------------------------------------
    # Compute
    # ------------------------------------------------------------------
    def _compute_upi_qr(self):
        for doc in self:
            doc.upi_qr_uri = False
            doc.upi_qr_image = False
            doc.upi_qr_amount = 0.0
            doc.upi_qr_fx_note = False
            company = doc._upi_qr_get_company()
            if not company or not self._upi_qr_is_valid_id(company.upi_qr_id) or not doc._upi_qr_is_applicable():
                continue
            currency = doc._upi_qr_get_currency()
            amount = doc._upi_qr_get_amount()
            if not currency or currency.compare_amounts(amount, 0.0) <= 0:
                continue
            inr_amount, fx_note = self._upi_qr_convert(amount, currency, company, doc._upi_qr_get_date())
            if inr_amount <= 0:
                continue
            reference = doc._upi_qr_get_reference()
            uri = self._upi_qr_build_uri(
                company.upi_qr_id,
                company.upi_qr_payee_name or company.name,
                inr_amount,
                reference=reference,
                note=_("Payment for %s", reference) if reference else None,
            )
            doc.upi_qr_uri = uri
            doc.upi_qr_amount = inr_amount
            doc.upi_qr_fx_note = fx_note
            try:
                doc.upi_qr_image = self._upi_qr_render(uri)
            except Exception:  # noqa: BLE001 - never break a report over a QR
                _logger.exception("UPI QR rendering failed for %s", doc)
                doc.upi_qr_image = False
