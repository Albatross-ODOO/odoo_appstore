from odoo import fields
from odoo.exceptions import ValidationError
from odoo.tests import tagged

from odoo.addons.account.tests.common import AccountTestInvoicingCommon


@tagged('post_install', '-at_install')
class TestUpiQr(AccountTestInvoicingCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # 1 USD (company currency) = 83 INR
        cls.inr = cls.setup_other_currency('INR', rates=[('2016-01-01', 83.0)])
        cls.company = cls.env.company
        cls.company.write({
            'upi_qr_id': 'Albatross@OkHDFCbank',
            'upi_qr_payee_name': 'Albatross Pvt. Ltd',
        })
        cls.mixin = cls.env['upi.qr.mixin']
        cls.company_data_2 = cls.setup_other_company()
        # the accounting test user also needs to create sale orders
        group = cls.env.ref('sales_team.group_sale_manager').sudo()
        users_field = 'user_ids' if 'user_ids' in group._fields else 'users'
        group.write({users_field: [(4, cls.env.user.id)]})
        cls.env.registry.clear_cache()

    # ------------------------------------------------------------------
    # helpers
    # ------------------------------------------------------------------
    def _invoice(self, amount=12980.0, currency=None, move_type='out_invoice', post=True):
        return self.init_invoice(
            move_type, partner=self.partner_a, invoice_date='2026-09-22', post=post,
            amounts=[amount], taxes=self.env['account.tax'], currency=currency or self.inr,
        )

    def _pay(self, invoice, amount):
        self.env['account.payment.register'].with_context(
            active_model='account.move', active_ids=invoice.ids,
        ).create({'amount': amount, 'payment_date': '2026-09-22'})._create_payments()

    def _order(self, amount=49560.0, currency=None):
        # the order currency follows the pricelist
        pricelist = self.env['product.pricelist'].create({
            'name': 'UPI test pricelist',
            'currency_id': (currency or self.inr).id,
            'company_id': self.company.id,
        })
        tax_field = 'tax_ids' if 'tax_ids' in self.env['sale.order.line']._fields else 'tax_id'
        return self.env['sale.order'].create({
            'partner_id': self.partner_a.id,
            'pricelist_id': pricelist.id,
            'order_line': [(0, 0, {
                'product_id': self.product_a.id,
                'product_uom_qty': 1,
                'price_unit': amount,
                tax_field: [(5, 0, 0)],
            })],
        })

    def _render(self, report_ref, records):
        html = self.env['ir.actions.report']._render_qweb_html(report_ref, records.ids)[0]
        return html.decode() if isinstance(html, bytes) else html

    # ------------------------------------------------------------------
    # company settings
    # ------------------------------------------------------------------
    def test_upi_id_normalised_and_validated(self):
        self.assertEqual(self.company.upi_qr_id, 'albatross@okhdfcbank')
        with self.assertRaises(ValidationError):
            self.company.upi_qr_id = 'not a upi id'
        with self.assertRaises(ValidationError):
            self.company.upi_qr_id = 'missing-at-sign'

    def test_uri_builder(self):
        uri = self.mixin._upi_qr_build_uri(
            'Business@OkHDFCbank', 'Albatross Pvt. Ltd', 12980, reference='INV/2026/00042',
            note='Payment for INV/2026/00042')
        self.assertTrue(uri.startswith('upi://pay?'))
        self.assertIn('pa=business%40okhdfcbank', uri)
        self.assertIn('pn=Albatross%20Pvt%20Ltd', uri)
        self.assertIn('am=12980.00', uri)
        self.assertIn('cu=INR', uri)
        self.assertIn('tn=Payment%20for%20INV%2F2026%2F00042', uri)
        self.assertIn('tr=INV%2F2026%2F00042', uri)
        self.assertNotIn('.', self.mixin._upi_qr_clean_payee('Albatross Pvt. Ltd'))
        self.assertTrue(self.mixin._upi_qr_is_valid_id('9876543210@ybl'))
        self.assertFalse(self.mixin._upi_qr_is_valid_id('a@'))

    def test_settings_preview(self):
        settings = self.env['res.config.settings'].create({})
        self.assertTrue(settings.upi_qr_preview)
        self.assertIn('Albatross Pvt Ltd', settings.upi_qr_preview_info)
        # while typing (no save yet) the preview explains what is wrong ...
        draft = self.env['res.config.settings'].new({'company_id': self.company.id, 'upi_qr_id': 'broken'})
        self.assertFalse(draft.upi_qr_preview)
        self.assertIn('does not look like', draft.upi_qr_preview_info)
        # ... and saving an invalid UPI ID is refused
        with self.assertRaises(ValidationError):
            settings.upi_qr_id = 'broken'

    # ------------------------------------------------------------------
    # invoices
    # ------------------------------------------------------------------
    def test_invoice_inr(self):
        inv = self._invoice()
        self.assertTrue(inv.upi_qr_image)
        self.assertIn('am=12980.00', inv.upi_qr_uri)
        self.assertIn('pa=albatross%40okhdfcbank', inv.upi_qr_uri)
        self.assertIn('tr=' + inv.name.replace('/', '%2F'), inv.upi_qr_uri)
        self.assertEqual(inv.upi_qr_amount, 12980.0)
        self.assertFalse(inv.upi_qr_fx_note)
        self.assertEqual(inv._upi_qr_get_amount_label(), 'Invoice total')

    def test_invoice_draft_has_qr(self):
        inv = self._invoice(post=False)
        self.assertTrue(inv.upi_qr_image)
        self.assertIn('am=12980.00', inv.upi_qr_uri)

    def test_invoice_amount_mode(self):
        inv = self._invoice()
        self._pay(inv, 2980.0)
        self.assertEqual(inv.payment_state, 'partial')
        # default: grand total, even when part-paid
        self.assertIn('am=12980.00', inv.upi_qr_uri)
        self.company.upi_qr_amount_mode = 'due'
        inv.invalidate_recordset(['upi_qr_uri', 'upi_qr_image', 'upi_qr_amount', 'upi_qr_fx_note'])
        self.assertIn('am=10000.00', inv.upi_qr_uri)
        self.assertEqual(inv._upi_qr_get_amount_label(), 'Amount due')

    def test_invoice_paid_hidden(self):
        inv = self._invoice()
        self._pay(inv, 12980.0)
        self.assertIn(inv.payment_state, ('paid', 'in_payment'))
        self.assertFalse(inv.upi_qr_image)

    def test_invoice_other_types_hidden(self):
        self.assertFalse(self._invoice(move_type='out_refund').upi_qr_image)
        self.assertFalse(self._invoice(move_type='in_invoice').upi_qr_image)

    def test_invoice_cancelled_hidden(self):
        inv = self._invoice(post=False)
        inv.button_cancel()
        self.assertFalse(inv.upi_qr_image)

    def test_invoice_switch_off(self):
        self.company.upi_qr_on_invoice = False
        self.assertFalse(self._invoice().upi_qr_image)
        self.company.upi_qr_on_invoice = True
        self.company.upi_qr_id = False
        self.assertFalse(self._invoice().upi_qr_image)

    def test_invoice_usd_converted_to_inr(self):
        inv = self._invoice(amount=600.0, currency=self.company.currency_id)
        self.assertEqual(inv.currency_id.name, 'USD')
        self.assertTrue(inv.upi_qr_image)
        self.assertIn('am=49800.00', inv.upi_qr_uri)
        self.assertIn('cu=INR', inv.upi_qr_uri)
        self.assertEqual(inv.upi_qr_amount, 49800.0)
        self.assertIn('USD', inv.upi_qr_fx_note)

    def test_no_inr_rate_no_qr(self):
        self.inr.rate_ids.unlink()
        inv = self._invoice(amount=600.0, currency=self.company.currency_id)
        self.assertFalse(inv.upi_qr_image)
        settings = self.env['res.config.settings'].create({})
        self.assertTrue(settings.upi_qr_rate_warning)
        # INR documents never need a rate
        self.assertTrue(self._invoice().upi_qr_image)

    def test_invoice_report_contains_card(self):
        inv = self._invoice()
        html = self._render('account.report_invoice_with_payments', inv)
        self.assertIn('upi_qr_card', html)
        self.assertIn('albatross@okhdfcbank', html)
        self.company.upi_qr_on_invoice = False
        html = self._render('account.report_invoice_with_payments', inv)
        self.assertNotIn('upi_qr_card', html)

    # ------------------------------------------------------------------
    # sale orders
    # ------------------------------------------------------------------
    def test_sale_order_states(self):
        order = self._order()
        self.assertEqual(order.state, 'draft')
        self.assertTrue(order.upi_qr_image)
        self.assertIn('am=49560.00', order.upi_qr_uri)
        self.assertIn('tr=' + order.name, order.upi_qr_uri)
        self.assertEqual(order._upi_qr_get_amount_label(), 'Order total')
        order.action_confirm()
        self.assertTrue(order.upi_qr_image)
        order._action_cancel()
        self.assertFalse(order.upi_qr_image)

    def test_sale_order_switch_off(self):
        self.company.upi_qr_on_sale_order = False
        self.assertFalse(self._order().upi_qr_image)

    def test_sale_order_usd_converted(self):
        order = self._order(amount=600.0, currency=self.company.currency_id)
        self.assertIn('am=49800.00', order.upi_qr_uri)
        self.assertIn('USD', order.upi_qr_fx_note)

    def test_sale_order_report_contains_card(self):
        order = self._order()
        html = self._render('sale.report_saleorder', order)
        self.assertIn('upi_qr_card', html)
        self.assertIn('Order total', html)

    # ------------------------------------------------------------------
    # multi-company
    # ------------------------------------------------------------------
    def test_second_company_isolated(self):
        other = self.company_data_2['company']
        self.assertFalse(other.upi_qr_id)
        inv = self.init_invoice(
            'out_invoice', partner=self.partner_a, invoice_date='2026-09-22', post=True,
            amounts=[100.0], taxes=self.env['account.tax'], company=other,
        )
        self.assertFalse(inv.upi_qr_image)
