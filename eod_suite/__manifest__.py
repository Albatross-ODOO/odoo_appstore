# -*- coding: utf-8 -*-
{
    "name": 'EOD Suite - Done by End Of Day: Theme, Home, Focus and Mobile',
    "summary": 'EOD Suite gets your team to the end of the day with nothing left open: a calm frosted-glass Odoo in your colours, a Home for every role, Start my queue, split view, floating chatter and a mobile app experience without a mobile app.',
    "description": """
EOD Suite
=========
EOD stands for End Of Day. The suite turns Odoo into a calm, app-like workspace so every person finishes the
day with nothing left open:

* **EOD - Backend Theme** (web_theme_eod, on the aic_theme engine): frosted panes over a soft colour
  field, Lagoon colours, ready-made palettes or colours from the company logo, dark mode, line app icons.
* **Workspace** (aic_workspace): split view, floating chatter, Back and Home keys, the phone tab bar.
* **Home and Focus** (aic_home): a Home for every role and Start my queue, one task at a time.
* **Share on WhatsApp** (aic_send): send a record from its chatter with a ready message and link.

Works on Odoo Community and Enterprise. Nothing is sent to outside services.
    """,
    "version": "19.0.2.0.0",
    "category": "Themes/Backend",
    "author": "Albatross",
    "website": "https://albatross.work/",
    "license": "OPL-1",
    "depends": ["web_theme_eod", "aic_workspace", "aic_home", "aic_send"],
    "data": [],
    "images": ["static/description/banner.png"],
    "installable": True,
    "application": True,
    "auto_install": False,
}
