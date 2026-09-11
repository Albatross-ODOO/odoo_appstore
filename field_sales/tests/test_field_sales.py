# -*- coding: utf-8 -*-

from psycopg2.errors import NotNullViolation

from odoo.exceptions import ValidationError
from odoo.tests import TransactionCase, tagged
from odoo.tools import mute_logger


@tagged('post_install', '-at_install')
class TestFieldSales(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.rep = cls.env['res.users'].create({
            'name': 'Field Rep',
            'login': 'field_rep_test',
            'email': 'field.rep@example.com',
            'group_ids': [(6, 0, [
                cls.env.ref('base.group_user').id,
                cls.env.ref('field_sales.group_salesperson').id,
            ])],
        })
        cls.Session = cls.env['field.sales.session'].with_user(cls.rep)
        cls.Visit = cls.env['field.sales.visit']

    def _check_in(self):
        res = self.Session.action_kiosk_check_in(19.0760, 72.8777, False)
        return self.Session.browse(res['session_id'])

    def _complete_visit(self, session, visit_id=False, **kw):
        vals = dict(
            company_name='Acme Corporation', contact_name='Priya Sharma', phone='+919876543210',
            notes='Interested in a demo', latitude=19.0761, longitude=72.8778, accuracy=8.0,
            visit_image=False, check_in_time=False, email='priya@acme.example',
            create_contact_bool=True, create_lead_bool=True, partner_id=False, visit_id=visit_id,
        )
        vals.update(kw)
        return self.Visit.browse(session.action_log_visit(**vals))

    # ------------------------------------------------------------------
    # Session lifecycle
    # ------------------------------------------------------------------
    def test_check_in_creates_active_session(self):
        session = self._check_in()
        self.assertEqual(session.state, 'checked_in')
        self.assertEqual(session.user_id, self.rep)
        self.assertEqual(session.location_log_ids.mapped('log_type'), ['check_in'])
        self.assertEqual(self.rep.active_field_session_id, session)

    def test_only_one_active_session_per_user(self):
        self._check_in()
        with self.assertRaises(ValidationError):
            self._check_in()

    def test_check_out_requires_completed_visit(self):
        session = self._check_in()
        with self.assertRaises(ValidationError):
            session.action_kiosk_check_out(19.0760, 72.8777, False)

    def test_check_out_blocked_while_visit_in_progress(self):
        session = self._check_in()
        self._complete_visit(session)
        session.action_kiosk_start_visit(19.08, 72.88, 5.0)
        with self.assertRaises(ValidationError):
            session.action_kiosk_check_out(19.0760, 72.8777, False)

    def test_check_out_same_location(self):
        session = self._check_in()
        self._complete_visit(session)
        session.action_kiosk_check_out(19.0761, 72.8778, False)
        self.assertEqual(session.state, 'completed')
        self.assertEqual(session.location_verification, 'same')
        self.assertIn('check_out', session.location_log_ids.mapped('log_type'))

    def test_check_out_location_changed(self):
        session = self._check_in()
        self._complete_visit(session)
        session.action_kiosk_check_out(19.2, 72.9, False)
        self.assertEqual(session.location_verification, 'changed')

    # ------------------------------------------------------------------
    # Client visits
    # ------------------------------------------------------------------
    def test_start_visit_is_idempotent(self):
        session = self._check_in()
        first = session.action_kiosk_start_visit(19.08, 72.88, 5.0)
        second = session.action_kiosk_start_visit(19.08, 72.88, 5.0)
        self.assertEqual(first['visit_id'], second['visit_id'])
        visit = self.Visit.browse(first['visit_id'])
        self.assertEqual(visit.state, 'in_progress')
        self.assertEqual(visit.user_id, self.rep)
        self.assertEqual(session.total_visits, 0, "In-progress visits are not counted")

    def test_start_visit_requires_checked_in_session(self):
        session = self.Session.create({'user_id': self.rep.id})
        with self.assertRaises(ValidationError):
            session.action_kiosk_start_visit(19.08, 72.88, 5.0)

    def test_complete_started_visit(self):
        session = self._check_in()
        started = session.action_kiosk_start_visit(19.08, 72.88, 5.0)
        visit = self._complete_visit(session, visit_id=started['visit_id'])
        self.assertEqual(visit.id, started['visit_id'])
        self.assertEqual(visit.state, 'completed')
        self.assertEqual(visit.company_name, 'Acme Corporation')
        self.assertTrue(visit.check_out_time)
        self.assertGreaterEqual(visit.duration, 0.0)
        self.assertEqual(session.total_visits, 1)

    def test_log_visit_without_start(self):
        session = self._check_in()
        visit = self._complete_visit(session, check_in_time='2026-07-10T12:00:00.000Z')
        self.assertEqual(visit.state, 'completed')
        self.assertEqual(str(visit.check_in_time), '2026-07-10 12:00:00')

    def test_log_visit_ignores_foreign_visit_id(self):
        session = self._check_in()
        other_session = self.env['field.sales.session'].create({'user_id': self.env.user.id})
        foreign = self.Visit.create({'session_id': other_session.id, 'company_name': 'X', 'phone': '1'})
        visit = self._complete_visit(session, visit_id=foreign.id)
        self.assertNotEqual(visit, foreign)
        self.assertEqual(visit.session_id, session)

    # ------------------------------------------------------------------
    # Contact & lead generation, salesperson tagging
    # ------------------------------------------------------------------
    def test_contact_and_lead_tagged_with_salesperson(self):
        session = self._check_in()
        visit = self._complete_visit(session)
        partner = visit.partner_id
        self.assertTrue(partner)
        self.assertEqual(partner.name, 'Acme Corporation')
        self.assertTrue(partner.is_field_lead)
        self.assertIn('Field Lead', partner.category_id.mapped('name'))
        self.assertEqual(partner.user_id, self.rep, "Contact is assigned to the field salesperson")
        child = partner.child_ids
        self.assertEqual(child.mapped('name'), ['Priya Sharma'])
        self.assertEqual(child.user_id, self.rep)
        lead = visit.lead_id
        self.assertTrue(lead)
        self.assertEqual(lead.user_id, self.rep, "Lead is assigned to the field salesperson")
        self.assertEqual(lead.partner_id, partner)
        self.assertEqual(lead.email_from, 'priya@acme.example')

    def test_visit_log_only(self):
        session = self._check_in()
        visit = self._complete_visit(session, create_contact_bool=False, create_lead_bool=False)
        self.assertFalse(visit.partner_id)
        self.assertFalse(visit.lead_id)

    def test_existing_partner_is_reused_and_tagged(self):
        existing = self.env['res.partner'].create({'name': 'Bluewave Traders', 'phone': '+912066110044'})
        session = self._check_in()
        visit = self._complete_visit(session, company_name='Bluewave', phone='+912066110044',
                                     email=False, create_lead_bool=False)
        self.assertEqual(visit.partner_id, existing)
        self.assertTrue(existing.is_field_lead)
        self.assertEqual(existing.user_id, self.rep)
        self.assertEqual(self.env['res.partner'].search_count([('phone', '=', '+912066110044')]), 1)

    def test_existing_partner_salesperson_not_overwritten(self):
        other = self.env['res.users'].create({'name': 'Other', 'login': 'other_rep_test'})
        existing = self.env['res.partner'].create({'name': 'Nakamura Foods', 'email': 'orders@nakamura.example', 'user_id': other.id})
        session = self._check_in()
        visit = self._complete_visit(session, company_name='Nakamura', phone='+918022339900',
                                     email='orders@nakamura.example', create_lead_bool=False)
        self.assertEqual(visit.partner_id, existing)
        self.assertEqual(existing.user_id, other)

    def test_linked_partner_from_kiosk(self):
        existing = self.env['res.partner'].create({'name': 'Linked Co', 'phone': '+910000000001'})
        session = self._check_in()
        visit = self._complete_visit(session, partner_id=existing.id, create_contact_bool=False)
        self.assertEqual(visit.partner_id, existing)
        self.assertEqual(visit.lead_id.partner_id, existing)

    def test_company_and_phone_are_required(self):
        session = self._check_in()
        with self.assertRaises(NotNullViolation), mute_logger('odoo.sql_db'):
            self.Visit.create({'session_id': session.id, 'company_name': 'No Phone Co', 'phone': False})
        with self.assertRaises(NotNullViolation), mute_logger('odoo.sql_db'):
            self.Visit.create({'session_id': session.id, 'company_name': False, 'phone': '+911'})

    # ------------------------------------------------------------------
    # Access rules
    # ------------------------------------------------------------------
    def test_salesperson_sees_only_own_sessions(self):
        session = self._check_in()
        other = self.env['res.users'].create({
            'name': 'Other Rep', 'login': 'other_rep_rules_test',
            'group_ids': [(6, 0, [self.env.ref('base.group_user').id, self.env.ref('field_sales.group_salesperson').id])],
        })
        self.assertIn(session, self.Session.search([]))
        self.assertNotIn(session, self.env['field.sales.session'].with_user(other).search([]))
