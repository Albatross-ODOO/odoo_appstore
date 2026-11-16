from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class ResCompany(models.Model):
    _inherit = 'res.company'

    upi_qr_id = fields.Char(
        string="UPI ID",
        help="Your UPI Virtual Payment Address, e.g. business@okhdfcbank. Leave empty to switch the UPI QR off for this company.")
    upi_qr_payee_name = fields.Char(
        string="UPI Payee Name",
        help="Name shown in the customer's UPI app. Defaults to the company name. Letters, digits and spaces only.")
    upi_qr_caption = fields.Char(
        string="UPI QR Caption", translate=True,
        default=lambda self: self._default_upi_qr_caption(),
        help="Text printed under the QR code.")
    upi_qr_amount_mode = fields.Selection(
        [('total', "Grand Total"), ('due', "Amount Due")],
        string="Amount on UPI QR", default='total', required=True,
        help="Amount encoded in the invoice QR. Quotations and orders always use their total.")
    upi_qr_on_invoice = fields.Boolean(string="UPI QR on Customer Invoices", default=True)
    upi_qr_on_sale_order = fields.Boolean(string="UPI QR on Quotations & Orders", default=True)
    upi_qr_replace_native = fields.Boolean(
        string="Replace Odoo's Built-in Payment QR",
        help="Hide Odoo's standard bank / UPI payment QR on invoices when the Scan & Pay card is printed.")

    @api.model
    def _default_upi_qr_caption(self):
        return _("Scan with any UPI app - the amount and payee are pre-filled, just confirm with your UPI PIN.")

    @api.constrains('upi_qr_id')
    def _check_upi_qr_id(self):
        mixin = self.env['upi.qr.mixin']
        for company in self:
            if company.upi_qr_id and not mixin._upi_qr_is_valid_id(company.upi_qr_id):
                raise ValidationError(_(
                    "'%s' is not a valid UPI ID. Expected the form handle@bank, e.g. business@okhdfcbank.",
                    company.upi_qr_id))

    @api.constrains('upi_qr_payee_name')
    def _check_upi_qr_payee_name(self):
        for company in self:
            if company.upi_qr_payee_name and len(company.upi_qr_payee_name) > 99:
                raise ValidationError(_("The UPI payee name cannot be longer than 99 characters."))

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            self._upi_qr_normalise_vals(vals)
        return super().create(vals_list)

    def write(self, vals):
        self._upi_qr_normalise_vals(vals)
        return super().write(vals)

    @api.model
    def _upi_qr_normalise_vals(self, vals):
        if vals.get('upi_qr_id'):
            vals['upi_qr_id'] = vals['upi_qr_id'].strip().lower()
        return vals
