# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Discuss Chat Monitor',
    'version': '18.0.1.0.0',
    'category': 'Discuss/Administration',
    'summary': 'Monitor Discuss chat sessions in a dual-pane sidebar/chat interface',
    'description': """
Discuss Chat Monitor for Odoo 18
================================
This module allows authorized Chat Managers to monitor and view chat conversations held in Odoo Discuss.

Key Features:
-------------
* **Discuss Dual-Pane View**: Left sidebar displaying active Discuss chat sessions (Direct chats, Group chats, Channels) and right pane showing full conversation history.
* **Real-time Live Sync**: Instantly read channels created in Odoo Discuss.
* **Admin Access Security**: Dedicated security group restricting access strictly to Chat Managers.
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
