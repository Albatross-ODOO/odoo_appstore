# -*- coding: utf-8 -*-
"""Upgrade from 18.0.1.x: visits gained a workflow state.

Every visit logged by the previous version was created and completed in one
step, so any visit with a check-out time is a completed visit. Session
counters only count completed visits from this version on, so refresh them.
"""


def migrate(cr, version):
    cr.execute("""
        UPDATE field_sales_visit
           SET state = 'completed'
         WHERE check_out_time IS NOT NULL
           AND (state IS NULL OR state = 'draft')
    """)
    cr.execute("""
        UPDATE field_sales_session s
           SET total_visits = (
               SELECT COUNT(*) FROM field_sales_visit v
                WHERE v.session_id = s.id AND v.state = 'completed'
           )
    """)
