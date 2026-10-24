# -*- coding: utf-8 -*-
"""Bring a database from the pre-engine Slate modules onto the engine, in place.

Before the engine, Slate was web_theme_slate (the whole theme) + web_slate_workspace + slate_home + slate_send. They
became aic_theme (the engine) + aic_workspace + aic_home + aic_send, and web_theme_slate became the Slate look on top.
Odoo cannot rename an installed module, so upgrading Slate Suite runs this from aic_theme's pre_init_hook: aic_theme
is the first of the new modules Odoo installs, and the hook runs before any of their tables or records exist. It
renames, in SQL, everything the old modules created (records' xml ids, models and their tables, columns, fields,
selection values, parameters, view keys, client actions, the stored company palettes), so the new modules find their
data already there and every setting, palette, Home role and preference survives. Nothing happens on a database that
never had the old modules.
"""
import logging
import re

_logger = logging.getLogger(__name__)

MODS = {
    "web_theme_slate": "aic_theme",
    "web_slate_workspace": "aic_workspace",
    "slate_home": "aic_home",
    "slate_send": "aic_send",
}
KEEP = ("slate_suite",)


def rename(text):
    """The identifier rules of the engine split (modules, models, fields, xml ids, parameters, CSS)."""
    if text is None or any(k in text for k in KEEP):
        return text
    for old, new in MODS.items():
        text = re.sub(r"(?<![A-Za-z0-9])%s(?![A-Za-z0-9])" % old, new, text)
        text = text.replace(old + "_", new + "_")
    text = re.sub(r"(?<!TRAN)SLATE", "AIC", text.replace("o_theme_slate", "o_aic_theme"))
    text = re.sub(r"Slate(?=[A-Z_0-9])", "Aic", text)
    text = re.sub(r"(?<=[a-z0-9_])Slate", "Aic", text)
    return re.sub(r"(?<!tran)slate", "aic", text)


def _has_column(cr, table, column):
    cr.execute("SELECT 1 FROM information_schema.columns WHERE table_schema = 'public' AND table_name = %s AND column_name = %s",
               (table, column))
    return bool(cr.fetchone())


def migrate_from_slate(cr):
    """Rename the old Slate modules' data to the engine modules. Returns True when there was something to move."""
    if not _has_column(cr, "res_company", "slate_palette_mode"):
        return False
    _logger.info("aic_theme: moving the pre-engine Slate modules' data onto the engine")

    # 1. records' xml ids: the old modules' own ids move to the engine modules (web_theme_slate's data was the
    #    engine's: the Slate look of today ships none of it)
    for old, new in MODS.items():
        cr.execute("SELECT id, name FROM ir_model_data WHERE module = %s", (old,))
        for xid, name in cr.fetchall():
            cr.execute("UPDATE ir_model_data SET module = %s, name = %s WHERE id = %s", (new, rename(name), xid))
    # the three modules that no longer exist: what depended on them depends on their engine module, and the rows
    # stop claiming to be installed (their code is gone; their data now belongs to the engine modules)
    for old in ("web_slate_workspace", "slate_home", "slate_send"):
        cr.execute("UPDATE ir_module_module_dependency SET name = %s WHERE name = %s", (MODS[old], old))
        cr.execute("UPDATE ir_module_module SET state = 'uninstalled' WHERE name = %s AND state != 'uninstalled'", (old,))

    # 2. models, their tables and sequences, and every field pointing at them
    cr.execute("SELECT id, model FROM ir_model WHERE model LIKE 'slate.%%'")
    for mid, model in cr.fetchall():
        new_model = rename(model)
        cr.execute("UPDATE ir_model SET model = %s WHERE id = %s", (new_model, mid))
        cr.execute("UPDATE ir_model_fields SET model = %s WHERE model = %s", (new_model, model))
        cr.execute("UPDATE ir_model_fields SET relation = %s WHERE relation = %s", (new_model, model))
        for table, col in (("ir_act_window", "res_model"), ("ir_act_server", "model_name"), ("mail_activity", "res_model"),
                           ("mail_message", "model"), ("mail_followers", "res_model"), ("ir_attachment", "res_model")):
            if _has_column(cr, table, col):
                cr.execute('UPDATE "%s" SET "%s" = %%s WHERE "%s" = %%s' % (table, col, col), (new_model, model))
        old_table, new_table = model.replace(".", "_"), new_model.replace(".", "_")
        cr.execute("SELECT 1 FROM information_schema.tables WHERE table_schema = 'public' AND table_name = %s", (old_table,))
        if cr.fetchone():
            cr.execute('ALTER TABLE "%s" RENAME TO "%s"' % (old_table, new_table))
            cr.execute("SELECT 1 FROM pg_class WHERE relname = %s", (old_table + "_id_seq",))
            if cr.fetchone():
                cr.execute('ALTER SEQUENCE "%s_id_seq" RENAME TO "%s_id_seq"' % (old_table, new_table))

    # 3. columns named slate_* on any table, their field rows and selection values
    cr.execute("""SELECT table_name, column_name FROM information_schema.columns
                  WHERE table_schema = 'public' AND column_name LIKE '%%slate%%' AND column_name NOT LIKE '%%translat%%'""")
    for table, column in cr.fetchall():
        cr.execute('ALTER TABLE "%s" RENAME COLUMN "%s" TO "%s"' % (table, column, rename(column)))
    cr.execute("SELECT id, name FROM ir_model_fields WHERE name LIKE '%%slate%%' AND name NOT LIKE '%%translat%%'")
    for fid, name in cr.fetchall():
        cr.execute("UPDATE ir_model_fields SET name = %s WHERE id = %s", (rename(name), fid))
    cr.execute("SELECT id, value FROM ir_model_fields_selection WHERE value LIKE '%%slate%%'")
    for sid, value in cr.fetchall():
        cr.execute("UPDATE ir_model_fields_selection SET value = %s WHERE id = %s", (rename(value), sid))

    # 4. parameters, client actions, view keys
    cr.execute("SELECT id, key FROM ir_config_parameter WHERE key LIKE '%%slate%%'")
    for pid, key in cr.fetchall():
        cr.execute("UPDATE ir_config_parameter SET key = %s WHERE id = %s", (rename(key), pid))
    cr.execute("UPDATE ir_act_client SET tag = replace(tag, 'slate', 'aic') WHERE tag LIKE 'slate%%'")
    cr.execute("SELECT id, key FROM ir_ui_view WHERE key LIKE '%%slate%%'")
    for vid, key in cr.fetchall():
        if rename(key) != key:
            cr.execute("UPDATE ir_ui_view SET key = %s WHERE id = %s", (rename(key), vid))

    # 5. the stored company palettes are CSS naming the old body class and custom properties
    if _has_column(cr, "res_company", "aic_palette_light"):
        cr.execute("SELECT id, aic_palette_light, aic_palette_dark FROM res_company")
        for cid, light, dark in cr.fetchall():
            cr.execute("UPDATE res_company SET aic_palette_light = %s, aic_palette_dark = %s WHERE id = %s",
                       (rename(light), rename(dark), cid))

    # 6. asset records the old modules made at install (Community dark mode, Enterprise gantt) point at the old
    #    paths: Odoo makes them again; compiled bundles are rebuilt
    cr.execute("DELETE FROM ir_asset WHERE path LIKE ANY(%s)", (["%s/%%" % old for old in MODS],))
    cr.execute("DELETE FROM ir_attachment WHERE url LIKE '/web/assets/%%'")

    # 7. the look these companies had: Slate (web_theme_slate is upgraded in the same run)
    cr.execute("SELECT 1 FROM ir_config_parameter WHERE key = 'aic_theme.default_skin'")
    if not cr.fetchone():
        cr.execute("""INSERT INTO ir_config_parameter (key, value, create_uid, write_uid, create_date, write_date)
                      VALUES ('aic_theme.default_skin', 'slate', 1, 1, now() at time zone 'UTC', now() at time zone 'UTC')""")
    return True
