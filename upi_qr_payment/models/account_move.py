from odoo import _, api, fields, models


class AccountMove(models.Model):
    _name = 'account.move'
    _inherit = ['account.move', 'upi.qr.mixin']

    @api.depends(
        'amount_total', 'amount_residual', 'currency_id', 'move_type', 'state', 'payment_state',
        'invoice_date', 'name', 'payment_reference', 'company_id',
        'company_id.upi_qr_id', 'company_id.upi_qr_payee_name', 'company_id.upi_qr_on_invoice',
        'company_id.upi_qr_amount_mode',
    )
    def _compute_upi_qr(self):
        super()._compute_upi_qr()

    def _upi_qr_is_applicable(self):
        self.ensure_one()
        return (
            self.move_type in ('out_invoice', 'out_receipt')
            and self.state != 'cancel'
            and self.payment_state not in ('paid', 'in_payment', 'reversed')
            and self.company_id.upi_qr_on_invoice
        )

    def _upi_qr_use_amount_due(self):
        self.ensure_one()
        return self.company_id.upi_qr_amount_mode == 'due' and self.state == 'posted'

    def _upi_qr_get_amount(self):
        self.ensure_one()
        return self.amount_residual if self._upi_qr_use_amount_due() else self.amount_total

    def _upi_qr_get_amount_label(self):
        self.ensure_one()
        return _("Amount due") if self._upi_qr_use_amount_due() else _("Invoice total")

    def _upi_qr_get_reference(self):
        self.ensure_one()
        if self.payment_reference:
            return self.payment_reference
        return self.name if self.name and self.name != '/' else ''

    def _upi_qr_get_date(self):
        self.ensure_one()
        return self.invoice_date or fields.Date.context_today(self)
