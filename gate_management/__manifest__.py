{
    'name': 'Gate Management',
    'version': '18.0.2.0.0',
    'summary': 'Gate Desk: visitor, vehicle, material and workforce gate control built for the security guard',
    'description': """
Gate Desk: gate management for warehouses, plants and offices
=============================================================

A security-guard app and a manager back office in one module.

**Guard app (phone, tablet or laptop)**

- Gate Desk home with live inside / expected / exited counters
- Walk-in entry for visitors, commercial vehicles and material, with photo capture
- Verify invitation by 6-digit code or QR scan (works offline at the gate)
- Worker attendance with check-in, check-out, individual and common breaks
- Schedule visits and share digital gate passes by e-mail, PDF, link and WhatsApp (Enterprise)

**Back office (Gate Manager)**

- Entries kanban / list / form with full chatter and audit times
- Workforce profiles (CSV / XLSX import), shift logs and break logs
- Auto-exit of expired entries, duplicate-vehicle protection, multi-company rules

Works on Odoo Community and Enterprise. On Enterprise with the WhatsApp app installed,
the WhatsApp option appears automatically and sends passes through an approved Meta template.
""",
    'category': 'Services/Gate Management',
    'author': 'Albatross',
    'website': 'https://www.odoo.com/apps',
    'license': 'LGPL-3',
    'depends': ['base', 'mail', 'web'],
    'data': [
        'security/security_groups.xml',
        'security/ir.model.access.csv',
        'data/ir_sequence_data.xml',
        'data/cron.xml',
        'wizard/verify_otp_view.xml',
        'wizard/share_wizard_view.xml',
        'views/gate_entry_views.xml',
        'views/gate_worker_views.xml',
        'views/report_gate_pass.xml',
        'views/invitation_landing_page.xml',
        'views/menus.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'gate_management/static/lib/jsqr/jsQR.js',
            'gate_management/static/src/css/gate_desk.css',
            'gate_management/static/src/components/**/*',
        ],
        'web.assets_tests': [
            'gate_management/static/tests/tours/**/*',
        ],
    },
    'images': ['static/description/banner.png'],
    'installable': True,
    'application': True,
    'auto_install': False,
}
