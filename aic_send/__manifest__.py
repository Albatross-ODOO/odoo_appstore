# -*- coding: utf-8 -*-
{
    "name": "Share on WhatsApp",
    "summary": "Share any record on WhatsApp from its chatter: the contact's number, a ready message and, for "
               "quotations, invoices and purchase orders, a secure link to the document. No WhatsApp API needed.",
    "description": """
Share on WhatsApp
=================
A "WhatsApp" button in the chatter of every record. It opens a short sheet with the contact's number (in
international form) and a message written for the document (quotation, order, invoice, purchase order or any
record), including a secure customer-portal link when the record has one. "Open WhatsApp" opens WhatsApp Web or
the app with the message filled in; the share is logged on the record, and a draft quotation is marked as sent,
the same as sending it by email.

Works on Community and Enterprise and needs no WhatsApp Business account. Can be turned off in Settings.
    """,
    "version": "19.0.1.0.0",
    "category": "Productivity",
    "author": "Albatross",
    "website": "https://albatross.work/",
    "license": "OPL-1",
    "depends": ["mail", "portal", "aic_theme"],
    "data": [
        "security/ir.model.access.csv",
        "wizard/whatsapp_share_views.xml",
        "views/res_config_settings_views.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "aic_send/static/src/chatter/chatter_patch.js",
            "aic_send/static/src/chatter/chatter_patch.xml",
            "aic_send/static/src/composer/send_sheet.js",
            "aic_send/static/src/composer/send_sheet.xml",
            "aic_send/static/src/composer/send_sheet.scss",
        ],
    },
    "uninstall_hook": "uninstall_hook",
    "images": ["static/description/banner.png"],
    "installable": True,
    "application": False,
    "auto_install": False,
}
