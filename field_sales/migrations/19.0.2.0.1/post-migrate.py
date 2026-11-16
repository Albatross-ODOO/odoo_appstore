# -*- coding: utf-8 -*-
"""Upgrade from 19.0.2.0.0.

* The access-rights label on the user form read "Field Sales Tracking Privilege". The security
  records are noupdate, so rename them here, and only when the label was not customised.
* Client visits started in the kiosk used the placeholders "Pending Client Visit" / "Pending"
  until the rep filled in the client; they now read "Visit in progress" / "-".
"""
from odoo import SUPERUSER_ID, api

RENAMES = [
    ('field_sales.module_category_field_sales', 'Field Sales Tracking', 'Field Sales'),
    ('field_sales.privilege_field_sales', 'Field Sales Tracking Privilege', 'Field Sales'),
]


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    for xmlid, old_name, new_name in RENAMES:
        record = env.ref(xmlid, raise_if_not_found=False)
        if record and record.with_context(lang='en_US').name == old_name:
            record.with_context(lang='en_US').name = new_name
    cr.execute("""
        UPDATE field_sales_visit
           SET company_name = 'Visit in progress', phone = '-'
         WHERE state != 'completed'
           AND company_name = 'Pending Client Visit'
           AND phone = 'Pending'
    """)
