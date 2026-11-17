# -*- coding: utf-8 -*-
"""EOD is one module, eod_glass_backend_theme ("EOD - Glass Backend Theme"). It takes over earlier installs: the six-module package (aic_theme,
aic_home, aic_workspace, aic_send, eod_suite) and the store module before the rename, web_theme_eod. On a database that has
them (upgrade: migrations/*4.0.0/pre-migrate.py; install over them: pre_init_hook) their records move onto eod_glass_backend_theme
before the new code loads, and the old modules stop claiming to be installed without running their uninstall (which
would drop the data). Model, field and parameter names did not change, so tables, settings, palettes and Home roles
all stay. Plain SQL: it runs before the registry knows EOD."""
import logging

from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

OLD = ("aic_theme", "aic_home", "aic_workspace", "aic_send", "eod_suite", "web_theme_eod")
NEW = "eod_glass_backend_theme"
ADOPTERS = OLD + (NEW, "web_theme_glass", "glass_suite")


def adopt_package(cr):
    cr.execute("SELECT id, name FROM ir_module_module WHERE name IN %s AND state NOT IN ('uninstalled', 'uninstallable')",
               (OLD,))
    old = cr.fetchall()
    if not old:
        return False
    # another app built on the separate modules (a second look, say) would load the engine twice
    cr.execute("""SELECT DISTINCT m.shortdesc->>'en_US' FROM ir_module_module_dependency d
                    JOIN ir_module_module m ON m.id = d.module_id
                   WHERE d.name IN %s AND m.name NOT IN %s AND m.state IN ('installed', 'to upgrade', 'to install')""",
               (OLD, ADOPTERS))
    others = [row[0] for row in cr.fetchall()]
    if others:
        raise UserError("EOD - Glass Backend Theme already contains the theme engine, Workspace, Home and Focus and Share on "
                        "WhatsApp. These apps still use the separate versions: %s. Uninstall them first, then install "
                        "EOD again." % ", ".join(others))
    cr.execute("SELECT id FROM ir_module_module WHERE name = %s", (NEW,))
    new_id = cr.fetchone()[0]
    _logger.info("eod_glass_backend_theme: moving %s into eod_glass_backend_theme", ", ".join(name for _id, name in old))
    for mod_id, name in old:
        # an xml id eod_glass_backend_theme already has (a field both extended) keeps eod_glass_backend_theme's row: same record
        cr.execute("""DELETE FROM ir_model_data d WHERE d.module = %s
                       AND EXISTS (SELECT 1 FROM ir_model_data n WHERE n.module = %s AND n.name = d.name)""", (name, NEW))
        cr.execute("UPDATE ir_model_data SET module = %s WHERE module = %s", (NEW, name))
        cr.execute("UPDATE ir_model_constraint SET module = %s WHERE module = %s", (new_id, mod_id))
        cr.execute("UPDATE ir_model_relation SET module = %s WHERE module = %s", (new_id, mod_id))
        cr.execute("DELETE FROM ir_module_module_dependency WHERE module_id = %s AND name = %s", (new_id, name))
        cr.execute("UPDATE ir_module_module SET state = 'uninstalled', latest_version = NULL WHERE id = %s", (mod_id,))
    # the lock rules (one module always has its look) and the asset records the parts made at their old paths:
    # init() makes the latter again at the new paths
    cr.execute("""DELETE FROM ir_asset WHERE name LIKE 'aic_lock:%%'
                   OR path LIKE 'aic_theme/%%' OR path LIKE 'aic_workspace/%%' OR path LIKE 'web_theme_eod/%%'""")
    cr.execute("""DELETE FROM ir_model_data WHERE module = %s AND model = 'ir.asset'
                   AND res_id NOT IN (SELECT id FROM ir_asset)""", (NEW,))
    return True
