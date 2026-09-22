{
    'name': 'UPI QR Payment on Invoice & Quotation',
    'version': '19.0.1.0.0',
    'summary': 'Scan & Pay: dynamic UPI QR code with the amount pre-filled on invoice and quotation PDFs - any UPI app, any currency',
    'description': """
UPI QR Payment on Invoice & Quotation
=====================================

Print a Scan & Pay card with a dynamic UPI QR code on every customer invoice and
quotation / sales order PDF. The customer scans it with any UPI app (PhonePe,
Google Pay, Paytm, BHIM, bank apps); the payee and the amount are already filled
in, they only confirm with their own UPI PIN.

- Works for any company: no Indian localisation module required
- Any document currency: USD, EUR, AED ... converted to INR with Odoo's exchange rates, original amount and rate printed on the card
- Configure once in Settings: UPI ID, payee name, caption, amount mode, switches per company
- Scan-to-verify preview in Settings before the first invoice goes out
- Optional switch to replace Odoo's built-in bank / UPI payment QR so the customer sees one code
- Multi-company safe, translatable, tested on Community and Enterprise

Odoo 19.0 - Community and Enterprise.
""",
    'category': 'Accounting/Accounting',
    'author': 'Albatross',
    'website': 'https://www.odoo.com/apps',
    'license': 'OPL-1',
    'price': 14.00,
    'currency': 'EUR',
    'depends': ['sale', 'account'],
    'data': [
        'views/res_config_settings_views.xml',
        'views/report_upi_qr_card.xml',
        'views/report_invoice.xml',
        'views/report_saleorder.xml',
    ],
    'assets': {
        'web.report_assets_common': [
            'upi_qr_payment/static/src/scss/upi_qr_report.scss',
        ],
        'web.assets_backend': [
            'upi_qr_payment/static/src/scss/upi_qr_settings.scss',
        ],
    },
    'images': ['static/description/banner.png'],
    'post_init_hook': 'upi_qr_post_init',
    'installable': True,
    'application': False,
    'auto_install': False,
}
