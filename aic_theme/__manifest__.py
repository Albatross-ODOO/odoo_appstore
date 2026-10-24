# -*- coding: utf-8 -*-
{
    "name": 'Backend Theme Engine',
    "summary": 'The engine behind the EOD backend theme: company colours from the logo, contrast-checked roles, dark mode, Community and Enterprise. Install a look (EOD) to switch it on.',
    "description": """
Backend Theme Engine
====================
The engine of the EOD backend theme (and of the looks to come). On its own it changes nothing: install a
look such as EOD (``web_theme_eod``) and the whole backend is restyled in it.

* Restyles buttons, inputs, dropdowns, dialogs, notifications, navbar, home menu (Enterprise),
  control panel, search, form / list / kanban / calendar / graph / pivot views, settings, and the
  Enterprise gantt / grid / cohort / map / hierarchy views, from one set of design tokens.
* One action colour, one "you are here" highlight and one ink per company: the look's own
  colours, colours taken from the company logo, or colours chosen by hand.
* Every colour is adjusted until its text passes WCAG AA, in light and in dark mode.
* A company palette is a few CSS variables in the page head. No extra RPC.
* Enable / disable at any time from *Settings > General Settings > Backend theme*. When more than
  one look is installed, each company picks its own there.
    """,
    "version": "19.0.1.2.1",
    "category": "Themes/Backend",
    "author": "Albatross",
    "website": "https://albatross.work/",
    "license": "OPL-1",
    "depends": ["web", "base_setup"],
    "data": [
        "views/webclient_templates.xml",
        "views/login_templates.xml",
        "views/res_config_settings_views.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "aic_theme/static/src/scss/tokens.scss",
            "aic_theme/static/src/scss/theme.scss",
            "aic_theme/static/src/scss/form_view.scss",
            "aic_theme/static/src/scss/discuss.scss",
            "aic_theme/static/src/scss/backlight.scss",
            "aic_theme/static/src/scss/mobile.scss",
            "aic_theme/static/src/scss/typography.scss",  # Inter + the seven-step scale (after the component layers: it wins ties)
            "aic_theme/static/src/scss/community.scss",   # Community-only rules (body.o_aic_community)
            "aic_theme/static/src/js/chart_palette.js",   # charts in the company palette while the look is on
            "aic_theme/static/src/js/font_regrow.js",     # text areas regrow once the bundled fonts have loaded
            "aic_theme/static/src/js/app_icons.js",       # line app icons (company setting "App icons")
        ],
        # the sign-in pages (web.login_layout), scoped to body.o_aic_login
        "web.assets_frontend": [
            "aic_theme/static/src/scss/login.scss",
        ],
        # the graph view is lazy-loaded with this bundle
        "web.assets_backend_lazy": [
            "aic_theme/static/src/js/graph_font.js",
        ],
        # Point of Sale UI (/pos/ui) — separate app bundle, themed self-contained
        "point_of_sale.assets_prod": [
            "aic_theme/static/src/js/pos_skin.js",
            "aic_theme/static/src/scss/pos.scss",
        ],
        "point_of_sale.assets_prod_dark": [
            "aic_theme/static/src/js/pos_skin.js",
            "aic_theme/static/src/scss/pos.scss",
            "aic_theme/static/src/scss/pos.dark.scss",
        ],
    },
    "images": ["static/description/banner.png"],
    "pre_init_hook": "pre_init_hook",
    "uninstall_hook": "uninstall_hook",
    "installable": True,
    "application": False,
    "auto_install": False,
}
