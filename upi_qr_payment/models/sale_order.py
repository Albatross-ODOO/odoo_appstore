from odoo import _, api, fields, models


class SaleOrder(models.Model):
    _name = 'sale.order'
    _inherit = ['sale.order', 'upi.qr.mixin']

    @api.depends(
        'amount_total', 'currency_id', 'state', 'date_order', 'name', 'company_id',
        'company_id.upi_qr_id', 'company_id.upi_qr_payee_name', 'company_id.upi_qr_on_sale_order',
    )
    def _compute_upi_qr(self):
        super()._compute_upi_qr()

    def _upi_qr_is_applicable(self):
        self.ensure_one()
        return self.state in ('draft', 'sent', 'sale') and self.company_id.upi_qr_on_sale_order

    def _upi_qr_get_amount(self):
        self.ensure_one()
        return self.amount_total

    def _upi_qr_get_amount_label(self):
        self.ensure_one()
        return _("Order total")

    def _upi_qr_get_reference(self):
        self.ensure_one()
        return self.name or ''

    def _upi_qr_get_date(self):
        self.ensure_one()
        return fields.Date.to_date(self.date_order) if self.date_order else fields.Date.context_today(self)
