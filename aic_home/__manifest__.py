# -*- coding: utf-8 -*-
{
    "name": "Home and Focus",
    "summary": "A role-aware start screen: what you missed, what is due today, the work that needs you, "
               "and your apps on one screen. Community and Enterprise.",
    "description": """
Home and Focus
==============
Replaces the app menu as the first screen after login (users who have their own home action keep it).

* Missed and Today: overdue activities with one-click Done, today's activities and meetings.
* A Home role per user (Sales, Warehouse, Purchase, Accounts, Service, Owner), chosen by an administrator or
  suggested from what the person actually works on. Each role gets its own KPI tiles and panels, built only
  for the apps that are installed and only from records the user can see.
* Backlog clean-up: a guided way to cancel old quotations and reschedule or cancel long-late transfers, with a
  preview, so Home counts stay meaningful.
* One server call per visit; no extra cost on other screens.
    """,
    "version": "20.0.1.1.2",
    "category": "Productivity",
    "author": "Albatross",
    "website": "https://albatross.work/",
    "license": "OPL-1",
    "price": 30.0,
    "currency": "EUR",
    "depends": ["web", "mail", "base_setup", "aic_theme"],
    "data": [
        "security/ir.access.csv",
        "data/home_action.xml",
        "views/res_users_views.xml",
        "views/res_config_settings_views.xml",
        "wizard/backlog_cleanup_views.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "aic_home/static/src/home/home.scss",
            "aic_home/static/src/home/home.js",
            "aic_home/static/src/home/home.xml",
            "aic_home/static/src/focus/focus.scss",
            "aic_home/static/src/focus/focus.js",
            "aic_home/static/src/focus/focus.xml",
            "aic_home/static/src/nav/home_key.scss",
            "aic_home/static/src/nav/home_key.js",
            ("prepend", "aic_home/static/src/nav/home_key.xml"),
        ],
    },
    "uninstall_hook": "uninstall_hook",
    "images": ["static/description/banner.png"],
    "installable": True,
    "application": False,
    "auto_install": False,
}
