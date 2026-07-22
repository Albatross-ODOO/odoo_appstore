# -*- coding: utf-8 -*-
{
    'name': 'Field Sales Activity & Tracking',
    'version': '19.0.1.0.0',
    'category': 'Sales/Sales',
    'summary': 'Kiosk Check-In, Geolocation Visit Tracking and Lead Capture for Field Sales',
    'description': """
        Track field sales representative activities:
        - Kiosk mode check-in with GPS and photo capture
        - Geolocation check-out and client visit logs
        - Automated res.partner lead generation with 'Field Lead' tags
        - Real-time location trajectory and route visualization
        - Manager dashboards and End-of-Day PDF reporting
    """,
    'author': 'Albatross',
    'license': 'OPL-1',
    'price': 19.99,
    'currency': 'EUR',

    'depends': ['base', 'web'],

    'data': [
        'security/field_sales_groups.xml',
        'security/field_sales_rules.xml',
        'security/ir.model.access.csv',
        'report/field_sales_session_report.xml',
        'views/field_sales_session_views.xml',
        'views/field_sales_visit_views.xml',
        'views/res_partner_views.xml',
        'views/field_sales_menus.xml',
    ],

    'assets': {
        'web.assets_backend': [
            'field_sales/static/src/libs/leaflet/leaflet.css',
            'field_sales/static/src/libs/leaflet/leaflet.js',
            'field_sales/static/src/scss/field_sales.scss',
            'field_sales/static/src/xml/session_route_map.xml',
            'field_sales/static/src/xml/field_sales_kiosk.xml',
            'field_sales/static/src/js/session_route_map.js',
            'field_sales/static/src/js/field_sales_kiosk.js',
        ],
    },

    'images': [
        'static/description/banner.png'
    ],

    'installable': True,
    'application': True,
}