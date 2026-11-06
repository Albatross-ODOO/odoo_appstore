# -*- coding: utf-8 -*-
from . import models

SKIN = "eod"
OLD = {"web_theme_glass": "web_theme_eod", "glass_suite": "eod_suite"}   # the look's earlier name


def pre_init_hook(env):
    """Upgrading from the earlier Glass look: EOD adopts its data instead of starting over.

    Glass and EOD are the same look under a new name. When web_theme_glass is installed, its records
    (settings view, palette fields such as the colour-field tint, the selection value) move to EOD's modules
    in place, the companies and the default look switch from "glass" to "eod", and the old modules are marked
    uninstalled without running their uninstall (which would drop that data). Nothing happens otherwise.
    """
    cr = env.cr
    cr.execute("SELECT name FROM ir_module_module WHERE name IN %s AND state IN ('installed', 'to upgrade')", (tuple(OLD),))
    old = [r[0] for r in cr.fetchall()]
    if not old:
        return
    for name in old:
        cr.execute("UPDATE ir_model_data SET module = %s WHERE module = %s", (OLD[name], name))
        cr.execute("UPDATE ir_module_module SET state = 'uninstalled', latest_version = NULL WHERE name = %s", (name,))
    # the look's key: company choice, the default for new companies, and the selection value's own record
    cr.execute("UPDATE res_company SET aic_skin = 'eod' WHERE aic_skin = 'glass'")
    cr.execute("UPDATE ir_config_parameter SET value = 'eod' WHERE key = 'aic_theme.default_skin' AND value = 'glass'")
    cr.execute("""UPDATE ir_model_data SET name = 'selection__res_company__aic_skin__eod'
                   WHERE module = 'web_theme_eod' AND name = 'selection__res_company__aic_skin__glass'""")
    cr.execute("""UPDATE ir_model_fields_selection SET value = 'eod', name = '{"en_US": "EOD"}'
                   WHERE value = 'glass' AND field_id IN (SELECT id FROM ir_model_fields
                                                          WHERE model = 'res.company' AND name = 'aic_skin')""")
    # tell post_init_hook this was an upgrade: each company keeps the look it had
    cr.execute("""INSERT INTO ir_config_parameter (key, value, create_date, write_date)
                  VALUES ('web_theme_eod.from_glass', '1', now() at time zone 'UTC', now() at time zone 'UTC')
                  ON CONFLICT (key) DO UPDATE SET value = '1'""")


def post_init_hook(env):
    """The look a buyer just installed is the one they expect to see: make it the default and give it to
    every company (a company can switch back in Settings when another look is installed too)."""
    params = env["ir.config_parameter"].sudo()
    upgraded = params.search([("key", "=", "web_theme_eod.from_glass")])
    if upgraded:
        upgraded.unlink()      # an upgrade from Glass (pre_init_hook): every company keeps its look
        return
    params.set_str("aic_theme.default_skin", SKIN)
    env["res.company"].sudo().search([]).write({"aic_skin": SKIN})


def uninstall_hook(env):
    """Leave nothing behind: the default look points elsewhere once this one is gone."""
    params = env["ir.config_parameter"].sudo()
    params.search([("key", "=", "aic_theme.default_skin"), ("value", "=", SKIN)]).unlink()
