# -*- coding: utf-8 -*-
{
    "name": 'EOD - Backend Theme',
    "summary": 'EOD (End Of Day) makes Odoo 20.0 calm and clear: frosted panes in your colours, an app-like phone layout, line app icons, readable in light and dark, Community and Enterprise.',
    "description": """
EOD Backend Theme
=================
EOD stands for End Of Day: the moment your team reaches with nothing left open. The theme is the calm half of
that promise. The whole Odoo 20.0 backend sits on frosted panes over a soft colour field, with one colour that
says "act here" and a pale one for "you are here".

* Panes, not borders: forms become a set of panes (status, title, field groups, lines, chatter),
  list rows are slim panes, kanban lanes are faint glass.
* Lagoon colours by default, two ready-made palettes (Graphite & Mint, Iris & Apricot), the
  company logo's colours, or colours chosen by hand. The colour field follows the palette.
* Every colour is adjusted until its text passes WCAG AA, in light and in dark mode.
* Blur only where it is cheap: containers blur, rows and cards do not; a solid fallback for
  browsers without backdrop-filter and for people who ask the system for less transparency.
* Point of Sale and the sign-in page in EOD, light and dark.
* Bundled Geist font (SIL Open Font License); nothing is loaded from outside services.

EOD is a look for the Backend Theme Engine (``aic_theme``), which it installs. Installing it on a database
that has the earlier Glass look moves every setting across automatically.
    """,
    "version": "20.0.3.0.0",
    "category": "Themes/Backend",
    "author": "Albatross",
    "website": "https://albatross.work/",
    "license": "OPL-1",
    "price": 120.0,
    "currency": "EUR",
    "depends": ["aic_theme"],
    "data": [
        "views/res_config_settings_views.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "web_theme_eod/static/src/scss/eod_tokens.scss",
            "web_theme_eod/static/src/scss/eod.scss",
        ],
        "web.assets_frontend": [
            "web_theme_eod/static/src/scss/eod_login.scss",
        ],
        # Point of Sale (/pos/ui): its own bundles, light and dark (the engine puts the look's class on <html>)
        "point_of_sale.assets_prod": [
            "web_theme_eod/static/src/scss/eod_pos.scss",
        ],
        "point_of_sale.assets_prod_dark": [
            "web_theme_eod/static/src/scss/eod_pos.scss",
            "web_theme_eod/static/src/scss/eod_pos.dark.scss",
        ],
    },
    "images": ["static/description/banner.png"],
    "pre_init_hook": "pre_init_hook",
    "post_init_hook": "post_init_hook",
    "uninstall_hook": "uninstall_hook",
    "installable": True,
    "application": False,
    "auto_install": False,
}
