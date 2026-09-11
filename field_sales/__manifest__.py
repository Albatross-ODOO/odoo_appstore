# -*- coding: utf-8 -*-
{
    'name': 'Field Sales Activity & Tracking',
    'version': '19.0.2.0.0',
    'category': 'Sales/Sales',
    'summary': 'Kiosk Check-In, Geolocation Visit Tracking and Lead Capture for Field Sales',
    'description': """
Field Sales Activity & Tracking
===============================

Track what your field sales representatives do during the day:

* Kiosk mode check-in with GPS lock and selfie verification
* Client visit check-in / check-out with photo and location
* Step-by-step client visit form (one field at a time, mobile friendly)
* Automatic contact and CRM lead creation, tagged "Field Lead" and
  assigned to the salesperson who generated them
* Route trajectory map with interval pings
* Manager dashboards and end-of-day PDF session report
""",
    'author': 'Albatross',
    'license': 'OPL-1',
    'price': 19.99,
    'currency': 'EUR',

    'depends': ['base', 'web', 'crm'],

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
        'static/description/banner.png',
    ],

    'installable': True,
    'application': True,
}
