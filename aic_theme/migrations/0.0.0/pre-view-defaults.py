# -*- coding: utf-8 -*-
"""Runs before every upgrade of this module (Odoo's "0.0.0" migration folder).

Website adds a required ``visibility`` column to ``ir_ui_view`` with no database default. During an
upgrade Odoo loads the modules in dependency order, and this module comes before Website, so the
registry does not know that column yet when this module creates a new view: the insert leaves it NULL
and the whole upgrade stops on the NOT NULL constraint. Giving the column the field's own default
('public', as declared in website/models/ir_ui_view.py) lets the insert through and changes nothing else.
"""


def migrate(cr, version):
    cr.execute("""
        SELECT 1 FROM information_schema.columns
         WHERE table_name = 'ir_ui_view' AND column_name = 'visibility'
           AND is_nullable = 'NO' AND column_default IS NULL
    """)
    if cr.fetchone():
        cr.execute("ALTER TABLE ir_ui_view ALTER COLUMN visibility SET DEFAULT 'public'")
