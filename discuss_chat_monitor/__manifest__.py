# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Discuss Chat Monitor',
    'version': '19.0.1.0.0',
    'category': 'Discuss/Administration',
    'summary': 'Monitor Discuss chat sessions in a dual-pane sidebar/chat interface',
    'description': """
Discuss Chat Monitor for Odoo 19
=================================
Allows administrators and managers to monitor, inspect, and filter Discuss chat conversations
in real time via a modern dual-pane UI.
    """,
    'author': 'Custom Odoo Team',
    'license': 'LGPL-3',
    'depends': [
        'base',
        'mail',
        'web',
    ],
    'data': [
        'security/chat_monitor_security.xml',
        'security/ir.model.access.csv',
        'views/discuss_chat_session_views.xml',
        'views/menu_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'discuss_chat_monitor/static/src/css/chat_monitor.css',
            'discuss_chat_monitor/static/src/js/chat_monitor.js',
            'discuss_chat_monitor/static/src/xml/chat_monitor.xml',
        ],
    },
    'installable': True,
    'application': True,
    'auto_install': False,
}
