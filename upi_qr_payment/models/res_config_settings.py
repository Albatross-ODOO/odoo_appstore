from odoo import _, api, fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    upi_qr_id = fields.Char(related='company_id.upi_qr_id', readonly=False)
    upi_qr_payee_name = fields.Char(related='company_id.upi_qr_payee_name', readonly=False)
    upi_qr_caption = fields.Char(related='company_id.upi_qr_caption', readonly=False)
    upi_qr_amount_mode = fields.Selection(related='company_id.upi_qr_amount_mode', readonly=False)
    upi_qr_on_invoice = fields.Boolean(related='company_id.upi_qr_on_invoice', readonly=False)
    upi_qr_on_sale_order = fields.Boolean(related='company_id.upi_qr_on_sale_order', readonly=False)
    upi_qr_replace_native = fields.Boolean(related='company_id.upi_qr_replace_native', readonly=False)

    upi_qr_preview = fields.Binary(string="UPI QR Preview", compute='_compute_upi_qr_preview')
    upi_qr_preview_info = fields.Char(compute='_compute_upi_qr_preview')
    upi_qr_rate_warning = fields.Char(compute='_compute_upi_qr_rate_warning')

    @api.depends('upi_qr_id', 'upi_qr_payee_name', 'company_id')
    def _compute_upi_qr_preview(self):
        mixin = self.env['upi.qr.mixin']
        for settings in self:
            settings.upi_qr_preview = False
            settings.upi_qr_preview_info = False
            upi_id = (settings.upi_qr_id or '').strip()
            if not upi_id:
                continue
            if not mixin._upi_qr_is_valid_id(upi_id):
                settings.upi_qr_preview_info = _("This does not look like a UPI ID. Expected handle@bank, e.g. business@okhdfcbank.")
                continue
            payee = settings.upi_qr_payee_name or settings.company_id.name
            uri = mixin._upi_qr_build_uri(upi_id, payee, 1.0, reference='VERIFY', note='Verification')
            settings.upi_qr_preview = mixin._upi_qr_render(uri, size=360)
            settings.upi_qr_preview_info = _(
                "Scan with your own UPI app: it should show \"%s\" as the payee with 1.00 pre-filled. Cancel, do not pay.",
                mixin._upi_qr_clean_payee(payee))

    @api.depends('company_id', 'upi_qr_id')
    def _compute_upi_qr_rate_warning(self):
        mixin = self.env['upi.qr.mixin']
        inr = mixin._upi_qr_get_inr()
        today = fields.Date.context_today(self)
        for settings in self:
            settings.upi_qr_rate_warning = False
            company = settings.company_id
            if not settings.upi_qr_id or not company or not inr or company.currency_id == inr:
                continue
            if not mixin._upi_qr_has_rate(inr, company, today):
                settings.upi_qr_rate_warning = _(
                    "%s runs in %s. Add an exchange rate for INR (Accounting > Configuration > Currencies) "
                    "so amounts can be converted; until then the UPI QR is not printed.",
                    company.name, company.currency_id.name)
