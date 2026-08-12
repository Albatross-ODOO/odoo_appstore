# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Discuss Chat Monitor & Compliance',
    'version': '18.0.1.0.0',
    'category': 'Discuss/Administration',
    'summary': 'Monitor direct employee chat sessions, view daily discussion transcripts, compliance audit logs & live updates',
    'description': """
Discuss Chat Monitor for Odoo 18
================================
This module allows authorized System Administrators and HR Compliance Officers to monitor and audit chat conversations held in Odoo Discuss.

Key Features:
-------------
* **Admin Access Security**: Dedicated security group restricting access strictly to authorized Chat Managers/Admins.
* **Employee Chat Directory**: Overview of employees with chat partner counts, last active timestamps, and quick session links.
* **Daily Chat Sessions (`discuss.chat.session`)**: Automatic grouping of 1-on-1 direct chats and group discussions by date and participant pairs.
* **Live Chat Stream**: Real-time message synchronization displaying updated chat messages instantly.
* **Rich Modern Chat UI**: Styled messaging thread with avatar bubbles, status badges, formatted text, and attachment previews.
* **Audit Trail & Flagging**: Tracks admin chat log viewing for compliance and allows flagging sessions with sensitive content.
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
        'data/cron_data.xml',
        'views/audit_log_views.xml',
        'views/discuss_chat_session_views.xml',
        'views/employee_chat_views.xml',
        'views/menu_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'discuss_chat_monitor/static/src/css/chat_monitor.css',
        ],
    },
    'installable': True,
    'application': True,
    'auto_install': False,
}
