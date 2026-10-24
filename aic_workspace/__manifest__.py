# -*- coding: utf-8 -*-
{
    "name": "Workspace - Split View, Left Pane, Mobile Shell",
    "summary": "Per-user navigation preference (Odoo top bar or a left pane), Split Form View "
               "beside list & kanban, floating chatter and an app-like phone shell — built on the backend theme engine.",
    "description": """
Workspace
=========
Adds the behaviours the theme cannot do with CSS alone. Everything is a per-user
preference (My Preferences → Workspace) and defaults to stock Odoo behaviour:

* **Split Form View** — with the switch on, opening a record from a list or kanban shows its
  form in a panel beside the list instead of navigating away. The panel *is* Odoo's own form
  view (header buttons, statusbar, sheet, chatter); nothing is redrawn.
* **Left pane** — optional application pane (full or icons) next to the untouched top bar.
* **Mobile shell** — a bottom tab bar on phones (Apps · Menu · Activity · Account) that opens
  Odoo's own app drawer, activity menu and account menu (restyled by the theme), a stage picker
  for grouped kanbans, a settings-section picker, "Show more" per stacked stage, previous / next
  and a month picker in the calendar, and a vertical gantt.
* **Floating chatter** — on the desktop split view the chatter pops out into a movable,
  resizable window that follows the selected record; on phones a button in the form, on
  kanban cards and list rows opens the record's chatter in a small window, full screen or a
  bubble. It is Odoo's own chatter — any model with mail.thread, custom modules included.
    """,
    "version": "20.0.1.1.0",
    "category": "Themes/Backend",
    "author": "Albatross",
    "website": "https://albatross.work/",
    "license": "OPL-1",
    "depends": ["web", "mail", "aic_theme"],
    # Preferences live entirely in the slide-out panel + session_info, so we never touch Odoo's own
    # user/settings views (keeps stock Odoo forms exactly as shipped). The one template brands the
    # installed app (window colour, iOS icon) in the page head.
    "data": [
        "data/lock_assets.xml",
        "views/webclient_templates.xml", "views/mail_activity_views.xml", "views/res_partner_views.xml"],
    "assets": {
        # the pivot and graph views are lazy-loaded with this bundle
        "web.assets_backend_lazy": [
            "aic_workspace/static/src/views/pivot_chart.js",
            "aic_workspace/static/src/views/pivot_chart.xml",
            "aic_workspace/static/src/views/graph_focus.js",
        ],
        "web.assets_backend": [
            # FIRST in the bundle: template extensions must precede every app's primary copy of
            # web.FormView / web.KanbanRecord / web.ListRenderer.RecordRow (Odoo applies to a
            # primary copy only the extensions registered before it) — stock apps and customer
            # modules alike get the phone chatter buttons this way.
            ("prepend", "aic_workspace/static/src/chatter/chatter_button.xml"),
            ("prepend", "aic_workspace/static/src/mobile/kanban_more.xml"),
            ("prepend", "aic_workspace/static/src/mobile/kanban_stage_chips.xml"),
            ("prepend", "aic_workspace/static/src/mobile/swipe_actions.xml"),
            ("prepend", "aic_workspace/static/src/mobile/search_sheet.xml"),
            ("prepend", "aic_workspace/static/src/mobile/calendar_nav.xml"),
            ("prepend", "aic_workspace/static/src/mobile/calendar_agenda.xml"),
            ("prepend", "aic_workspace/static/src/views/empty_state.xml"),
            # the navigation path (Back key · page button · pager)
            ("prepend", "aic_workspace/static/src/nav/crumbs.xml"),
            ("prepend", "aic_workspace/static/src/form/header_overflow.xml"),
            ("prepend", "aic_workspace/static/src/views/no_match.xml"),
            ("prepend", "aic_workspace/static/src/views/customer_overview.xml"),
            # saved searches as chips under the control panel (Core phase 5)
            ("prepend", "aic_workspace/static/src/favorites/favorite_chips.xml"),
            "aic_workspace/static/src/favorites/favorite_chips.js",
            "aic_workspace/static/src/favorites/favorite_chips.scss",
            "aic_workspace/static/src/nav/crumbs.js",
            "aic_workspace/static/src/form/header_overflow.js",
            "aic_workspace/static/src/form/header_overflow.scss",
            "aic_workspace/static/src/views/no_match.js",
            "aic_workspace/static/src/views/no_match.scss",
            "aic_workspace/static/src/views/customer_overview.js",
            "aic_workspace/static/src/views/customer_overview.scss",
            "aic_workspace/static/src/views/lost_one_tap.js",
            "aic_workspace/static/src/views/lost_one_tap.scss",
            "aic_workspace/static/src/views/last_message.js",
            "aic_workspace/static/src/views/last_message.xml",
            "aic_workspace/static/src/views/last_message.scss",
            "aic_workspace/static/src/keys/aic_keys.js",
            "aic_workspace/static/src/keys/aic_keys.xml",
            "aic_workspace/static/src/keys/aic_keys.scss",
            "aic_workspace/static/src/views/empty_state.js",
            "aic_workspace/static/src/views/empty_state.scss",
            "aic_workspace/static/src/prefs/density.scss",
            "aic_workspace/static/src/mobile/transitions.js",
            "aic_workspace/static/src/mobile/transitions.scss",
            "aic_workspace/static/src/views/archive_undo.js",
            "aic_workspace/static/src/views/stock_summary.js",
            "aic_workspace/static/src/views/stock_summary.xml",
            "aic_workspace/static/src/views/stock_summary.scss",
            "aic_workspace/static/src/views/purchase_summary.js",
            "aic_workspace/static/src/views/purchase_summary.xml",
            "aic_workspace/static/src/views/purchase_summary.scss",
            "aic_workspace/static/src/views/task_visit.js",
            "aic_workspace/static/src/views/task_visit.xml",
            "aic_workspace/static/src/views/task_visit.scss",
            "aic_workspace/static/src/mobile/scan_flash.js",
            "aic_workspace/static/src/mobile/scan_flash.scss",
            "aic_workspace/static/src/nav/crumbs.scss",
            "aic_workspace/static/src/prefs/aic_prefs_service.js",
            "aic_workspace/static/src/prefs/prefs_panel.js",
            "aic_workspace/static/src/prefs/prefs_panel.xml",
            "aic_workspace/static/src/prefs/prefs_panel.scss",
            "aic_workspace/static/src/prefs/user_menu_items.js",
            "aic_workspace/static/src/split/split_panel.js",
            "aic_workspace/static/src/split/split_panel.xml",
            "aic_workspace/static/src/split/split_panel.scss",
            "aic_workspace/static/src/split/split_views.js",
            "aic_workspace/static/src/split/split_views.xml",
            "aic_workspace/static/src/chatter/chatter_store.js",
            "aic_workspace/static/src/chatter/chatter_window.js",
            "aic_workspace/static/src/chatter/chatter_window.xml",
            "aic_workspace/static/src/chatter/chatter_window.scss",
            "aic_workspace/static/src/chatter/chatter_button.js",
            "aic_workspace/static/src/pane/left_pane.js",
            "aic_workspace/static/src/pane/left_pane.xml",
            "aic_workspace/static/src/pane/left_pane.scss",
            "aic_workspace/static/src/pane/navbar_toggle.js",
            ("prepend", "aic_workspace/static/src/pane/navbar_toggle.xml"),
            "aic_workspace/static/src/mobile/stage_store.js",
            "aic_workspace/static/src/mobile/kanban_stage_patch.js",
            "aic_workspace/static/src/mobile/kanban_stage_chips.js",
            "aic_workspace/static/src/mobile/kanban_stage_chips.scss",
            "aic_workspace/static/src/mobile/swipe_actions.js",
            "aic_workspace/static/src/mobile/swipe_actions.scss",
            "aic_workspace/static/src/mobile/search_sheet.js",
            "aic_workspace/static/src/mobile/search_sheet.scss",
            "aic_workspace/static/src/mobile/kanban_more.js",
            "aic_workspace/static/src/mobile/calendar_nav.js",
            "aic_workspace/static/src/mobile/calendar_agenda.js",
            "aic_workspace/static/src/mobile/calendar_agenda.scss",
            "aic_workspace/static/src/mobile/burger_menu.js",
            "aic_workspace/static/src/mobile/confirm_closes_sheet.js",
            "aic_workspace/static/src/search/record_commands.js",
            "aic_workspace/static/src/search/record_commands.xml",
            "aic_workspace/static/src/search/record_commands.scss",
            "aic_workspace/static/src/activity/date_picks.js",
            "aic_workspace/static/src/activity/date_picks.xml",
            "aic_workspace/static/src/activity/date_picks.scss",
            "aic_workspace/static/src/mobile/mobile_shell.js",
            "aic_workspace/static/src/mobile/mobile_shell.xml",
            "aic_workspace/static/src/mobile/mobile_shell.scss",
        ],
        # The phone gantt (static/src/mobile/gantt_phone.{xml,js,scss}) is NOT listed here: it
        # extends and imports Enterprise's web_gantt, which lives in the on-demand bundle
        # web.assets_backend_lazy. Community has that bundle too (Chart.js) but no web_gantt, so a
        # manifest entry made every Community graph screen log "Missing (extension) parent
        # templates" (BUG-0048). models/ir_http.py registers the three files as ir.asset records of
        # web.assets_backend_lazy (the template prepended) only where web_gantt is installed.
    },
    "uninstall_hook": "uninstall_hook",
    "images": ["static/description/banner.png"],
    "installable": True,
    "application": False,
    "auto_install": False,
}
