# -*- coding: utf-8 -*-

import unittest

from odoo.tests import HttpCase, tagged
from odoo.tests import common as tests_common


@tagged('post_install', '-at_install')
class TestFieldSalesUI(HttpCase):
    """Open every view of the module in a browser (kiosk, sessions, visits, prospects)."""
    browser_size = '1300,900'

    @classmethod
    def setUpClass(cls):
        if tests_common.websocket is None:
            # HttpCase would log a WARNING per test; skip the class quietly instead
            raise unittest.SkipTest("websocket-client module is not installed (browser tours need it)")
        super().setUpClass()
        cls.rep = cls.env['res.users'].create({
            'name': 'Field Rep UI',
            'login': 'field_rep_ui',
            'password': 'field_rep_ui',
            'email': 'field.rep.ui@example.com',
            'group_ids': [(6, 0, [
                cls.env.ref('base.group_user').id,
                cls.env.ref('field_sales.group_salesperson').id,
            ])],
        })
        Session = cls.env['field.sales.session'].with_user(cls.rep)
        res = Session.action_kiosk_check_in(19.0760, 72.8777, False)
        cls.fs_session = Session.browse(res['session_id'])
        # one completed visit (creates the "Acme Corporation" contact + lead) ...
        cls.fs_session.action_log_visit(
            'Acme Corporation', 'Priya Sharma', '+919876543210', 'Interested in a demo',
            19.0761, 72.8778, 8.0, False, False, 'priya@acme.example', True, True, False, False,
        )
        # ... and one visit in progress, so the kiosk shows the check-out form
        cls.fs_session.action_kiosk_start_visit(19.0800, 72.8800, 5.0)

    def test_kiosk_dashboard(self):
        self.start_tour('/odoo/action-field_sales.action_field_sales_kiosk_client_action',
                        'field_sales_kiosk_tour', login='field_rep_ui')

    def test_session_views_and_route_map(self):
        self.start_tour('/odoo/action-field_sales.action_field_sales_session',
                        'field_sales_session_tour', login='field_rep_ui')

    def test_visit_views(self):
        self.start_tour('/odoo/action-field_sales.action_field_sales_visit',
                        'field_sales_visit_tour', login='field_rep_ui')

    def test_prospects_and_partner_tab(self):
        self.start_tour('/odoo/action-field_sales.action_field_sales_leads',
                        'field_sales_prospects_tour', login='field_rep_ui')
