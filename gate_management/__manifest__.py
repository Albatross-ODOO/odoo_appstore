{
    'name': 'Gate Management',
    'version': '1.0.2',
    'summary': 'Warehouse Gate Management System',
    'description': """
        Manage incoming and outgoing gate entries for the warehouse.
        Features:
        - Security Guard and Admin roles
        - Incoming/Outgoing Flow
        - Barcode/QR Scanning support
        - Vendor OTP Verification
        - Photo Uploads
    """,
    'category': 'Warehouse',
    'author': 'Albatross',
    'depends': ['base', 'mail', 'web', 'whatsapp'],
    'data': [
        'security/security_groups.xml',
        'security/ir.model.access.csv',
        'data/ir_sequence_data.xml',
        'data/cron.xml',
        'data/whatsapp_template_data.xml',
        'wizard/verify_otp_view.xml',
        'wizard/share_wizard_view.xml',
        'wizard/worker_kiosk_search_view.xml',
        'views/gate_entry_views.xml',
        'views/gate_worker_views.xml',
        'views/menus.xml',
        'views/report_gate_pass.xml',
        'views/invitation_landing_page.xml',
    ],
    'demo': [],
    'installable': True,
    'application': True,
    'auto_install': False,
    'license': 'LGPL-3',
    'assets': {
        'web.assets_backend': [
            'gate_management/static/src/css/kiosk.css',
            'gate_management/static/src/components/camera_widget/camera_widget.xml',
            'gate_management/static/src/components/camera_widget/camera_widget.js',
            'gate_management/static/src/components/qr_scanner/qr_scanner.xml',
            'gate_management/static/src/components/qr_scanner/qr_scanner.js',
        ],
    },
}
