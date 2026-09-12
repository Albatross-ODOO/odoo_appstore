from datetime import timedelta

from odoo import fields
from odoo.exceptions import AccessError, ValidationError
from odoo.tests import TransactionCase, tagged


@tagged('post_install', '-at_install')
class TestGate(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.guard = cls.env['res.users'].create({
            'name': 'Guard Ramesh', 'login': 'guard_ramesh', 'email': 'guard@example.com',
            'groups_id': [(6, 0, [cls.env.ref('base.group_user').id, cls.env.ref('gate_management.group_gate_guard').id])],
        })
        cls.manager = cls.env['res.users'].create({
            'name': 'Gate Manager', 'login': 'gate_manager', 'email': 'manager@example.com',
            'groups_id': [(6, 0, [cls.env.ref('base.group_user').id, cls.env.ref('gate_management.group_gate_manager').id])],
        })
        cls.worker = cls.env['gate.worker'].create({'name': 'Rakesh Patel', 'worker_code': 'WRK042', 'mobile': '9879022314'})
        cls.worker2 = cls.env['gate.worker'].create({'name': 'Imran Sheikh', 'worker_code': 'WRK103', 'mobile': '9879099999'})

    # ---------------- entries ----------------
    def test_sequence_and_plate_normalisation(self):
        Entry = self.env['gate.entry']
        e_in = Entry.create({'entry_type': 'vehicle', 'vehicle_number': '  gj 05   bx 4821 ', 'visitor_name': 'Driver'})
        e_out = Entry.create({'entry_type': 'vehicle', 'operation_type': 'outgoing', 'vehicle_number': 'mh12kl2210'})
        self.assertTrue(e_in.name.startswith('IN/'))
        self.assertTrue(e_out.name.startswith('OUT/'))
        self.assertEqual(e_in.vehicle_number, 'GJ 05 BX 4821')
        self.assertEqual(e_out.vehicle_number, 'MH12KL2210')

    def test_walk_in_requires_photo_then_enters(self):
        entry = self.env['gate.entry'].create({'entry_type': 'visitor', 'visitor_name': 'Anita Shah', 'mobile_number': '9825041172'})
        with self.assertRaises(ValidationError):
            entry.action_confirm_entry()
        entry.entry_photo = b'aGVsbG8='
        action = entry.action_confirm_entry()
        self.assertEqual(entry.state, 'entered')
        self.assertTrue(entry.check_in_time)
        self.assertEqual(action['res_model'], 'gate.entry')  # lands on a fresh walk-in form
        entry.action_exit()
        self.assertEqual(entry.state, 'exited')
        self.assertTrue(entry.check_out_time)

    def test_material_enters_without_photo(self):
        entry = self.env['gate.entry'].create({'entry_type': 'material', 'material_name': '40 bags cement', 'material_qty': 40, 'material_flow': 'inward'})
        entry.action_confirm_entry()
        self.assertEqual(entry.state, 'entered')

    def test_duplicate_vehicle_inside_blocked(self):
        Entry = self.env['gate.entry']
        first = Entry.create({'entry_type': 'vehicle', 'vehicle_number': 'GJ 01 AA 1111', 'entry_photo': b'aGVsbG8='})
        first.action_confirm_entry()
        second = Entry.create({'entry_type': 'vehicle', 'vehicle_number': 'gj 01 aa 1111', 'entry_photo': b'aGVsbG8='})
        with self.assertRaises(ValidationError):
            second.action_confirm_entry()

    def test_repeat_visitor_autofill(self):
        Entry = self.env['gate.entry']
        Entry.create({'entry_type': 'visitor', 'visitor_name': 'Meera Joshi', 'mobile_number': '98241 77390', 'vehicle_number': 'GJ 05 ZZ 0001', 'host_id': self.manager.id})
        new = Entry.new({'entry_type': 'visitor', 'mobile_number': '+91 98241 77390'})
        new._onchange_mobile_number()
        self.assertEqual(new.visitor_name, 'Meera Joshi')
        self.assertEqual(new.vehicle_number, 'GJ 05 ZZ 0001')
        self.assertEqual(new.host_id, self.manager)

    def test_schedule_share_and_verify_flow(self):
        start = fields.Datetime.now() + timedelta(hours=1)
        entry = self.env['gate.entry'].create({
            'entry_type': 'visitor', 'visitor_name': 'Meera Joshi', 'mobile_number': '9824177390',
            'scheduled_start': start, 'scheduled_end': start + timedelta(hours=2),
        })
        entry.action_schedule()
        self.assertEqual(entry.state, 'scheduled')
        self.assertEqual(len(entry.otp), 6)
        self.assertTrue(entry.qr_code_image)
        self.assertIn('/gate/invitation/share?id=%d&token=%s' % (entry.id, entry.access_token), entry.share_link)
        self.assertIn(entry.otp, entry.invite_message)
        self.assertTrue(entry.validity_string)

        wizard = self.env['gate.verify.otp.wizard'].create({'otp_code': entry.otp})
        result = wizard.action_verify()
        self.assertEqual(result.get('res_model'), 'gate.verify.otp.wizard')
        self.assertEqual(wizard.state, 'photo')
        self.assertEqual(wizard.entry_id, entry)
        self.assertEqual(entry.state, 'authorized')
        self.assertFalse(wizard.window_expired)
        wizard.photo = b'aGVsbG8='
        wizard.action_confirm_verification()
        self.assertEqual(wizard.state, 'done')
        self.assertEqual(entry.state, 'entered')
        self.assertTrue(entry.entry_photo)

        # the same code again: already inside
        again = self.env['gate.verify.otp.wizard'].create({'otp_code': entry.otp})
        res = again.action_verify()
        self.assertEqual(res['tag'], 'display_notification')

        # share-link lookup (what the QR encodes)
        entry2 = self.env['gate.entry'].create({'entry_type': 'visitor', 'visitor_name': 'Link Visitor', 'scheduled_start': start, 'scheduled_end': start + timedelta(hours=1)})
        entry2.action_schedule()
        w2 = self.env['gate.verify.otp.wizard'].create({'otp_code': entry2.share_link})
        w2.action_verify()
        self.assertEqual(w2.entry_id, entry2)

    def test_cron_auto_exit(self):
        past = fields.Datetime.now() - timedelta(hours=3)
        entry = self.env['gate.entry'].create({'entry_type': 'visitor', 'visitor_name': 'Late Visitor', 'entry_photo': b'aGVsbG8=', 'scheduled_start': past, 'scheduled_end': past + timedelta(hours=1)})
        entry.action_confirm_entry()
        self.assertTrue(entry.is_overdue)
        self.env['gate.entry']._cron_auto_exit()
        self.assertEqual(entry.state, 'exited')

    def test_gate_desk_data(self):
        entry = self.env['gate.entry'].create({'entry_type': 'visitor', 'visitor_name': 'Anita Shah', 'entry_photo': b'aGVsbG8='})
        entry.action_confirm_entry()
        data = self.env['gate.entry'].with_user(self.guard).gate_desk_data()
        self.assertGreaterEqual(data['counts']['inside'], 1)
        self.assertIn(entry.id, [r['id'] for r in data['inside']])
        self.assertEqual(set(data['workforce']), {'inside', 'break', 'outside'})

    def test_gate_entries_data(self):
        Entry = self.env['gate.entry']
        v = Entry.create({'entry_type': 'vehicle', 'vehicle_number': 'GJ 09 QQ 1234', 'entry_photo': b'aGVsbG8='}); v.action_confirm_entry()
        m = Entry.create({'entry_type': 'material', 'material_name': 'Steel rods', 'material_slip_no': 'CH-77'}); m.action_confirm_entry()
        m.action_exit()
        data = Entry.with_user(self.guard).gate_entries_data('all', '')
        ids = [r['id'] for r in data['rows']]
        self.assertIn(v.id, ids)
        self.assertIn(m.id, ids)
        self.assertEqual([r['id'] for r in Entry.gate_entries_data('vehicle', '')['rows']], [v.id])
        self.assertEqual([r['id'] for r in Entry.gate_entries_data('exited', '')['rows']], [m.id])
        self.assertEqual([r['id'] for r in Entry.gate_entries_data('all', 'ch-77')['rows']], [m.id])
        row = next(r for r in data['rows'] if r['id'] == v.id)
        self.assertEqual(row['title'], 'GJ 09 QQ 1234')
        self.assertEqual(row['state'], 'entered')
        self.assertTrue(row['when'].startswith('in '))
        self.assertGreaterEqual(data['counts']['inside'], 1)

    # ---------------- workers ----------------
    def test_worker_check_in_break_check_out(self):
        w = self.worker
        self.assertEqual(w.current_state, 'outside')
        w.action_check_in()
        self.assertEqual(w.current_state, 'inside')
        entry = self.env['gate.entry'].search([('worker_id', '=', w.id), ('state', '=', 'entered')])
        self.assertEqual(len(entry), 1)
        w.action_check_in()  # idempotent
        self.assertEqual(len(w.log_ids), 1)

        w.action_start_break()
        self.assertEqual(w.current_state, 'break')
        self.assertEqual(len(w.break_ids), 1)
        w.action_end_break()
        self.assertEqual(w.current_state, 'inside')
        self.assertTrue(w.break_ids.end_time)

        w.action_start_break()
        w.action_check_out()  # check-out during a break closes the break too
        self.assertEqual(w.current_state, 'outside')
        self.assertTrue(all(w.break_ids.mapped('end_time')))
        self.assertEqual(w.log_ids.state, 'outside')
        self.assertEqual(entry.state, 'exited')
        self.assertGreaterEqual(w.log_ids.break_minutes, 0)

    def test_toggle_keeps_old_behaviour(self):
        self.worker.action_toggle_attendance()
        self.assertEqual(self.worker.current_state, 'inside')
        self.worker.action_toggle_attendance()
        self.assertEqual(self.worker.current_state, 'outside')

    def test_break_all_and_break_over_all(self):
        (self.worker | self.worker2).action_check_in()
        n = self.env['gate.worker'].action_break_all()
        self.assertEqual(n, 2)
        self.assertEqual(set((self.worker | self.worker2).mapped('current_state')), {'break'})
        n = self.env['gate.worker'].action_break_over_all()
        self.assertEqual(n, 2)
        self.assertEqual(set((self.worker | self.worker2).mapped('current_state')), {'inside'})

    def test_exit_worker_entry_closes_shift(self):
        self.worker.action_check_in()
        entry = self.env['gate.entry'].search([('worker_id', '=', self.worker.id), ('state', '=', 'entered')])
        self.worker.action_start_break()
        entry.action_exit()
        self.assertEqual(self.worker.current_state, 'outside')

    def test_kiosk_data_and_search(self):
        self.worker.action_check_in()
        Worker = self.env['gate.worker'].with_user(self.guard)
        data = Worker.kiosk_data('')
        by_id = {r['id']: r for r in data['rows']}
        self.assertEqual(by_id[self.worker.id]['state'], 'inside')
        self.assertTrue(by_id[self.worker.id]['since'])
        self.assertEqual(data['counts']['inside'], 1)
        self.assertEqual([r['id'] for r in Worker.kiosk_data('+91 98790 22314')['rows']], [self.worker.id])
        self.assertEqual([r['id'] for r in Worker.kiosk_data('wrk103')['rows']], [self.worker2.id])
        self.assertEqual(Worker.kiosk_data('nobody')['rows'], [])

    # ---------------- access ----------------
    def test_guard_can_record_attendance_but_not_edit_profiles(self):
        worker = self.worker.with_user(self.guard)
        with self.assertRaises(AccessError):
            worker.write({'name': 'Hacked'})
        worker.action_check_in()
        self.assertEqual(self.worker.current_state, 'inside')
        worker.action_start_break()
        worker.action_check_out()
        self.assertEqual(self.worker.current_state, 'outside')
        entry = self.env['gate.entry'].with_user(self.guard).create({'entry_type': 'visitor', 'visitor_name': 'Guard Made', 'entry_photo': b'aGVsbG8='})
        entry.action_confirm_entry()
        with self.assertRaises(AccessError):
            entry.unlink()

    def test_portal_user_cannot_record_attendance(self):
        portal = self.env['res.users'].create({'name': 'Portal', 'login': 'portal_x', 'groups_id': [(6, 0, [self.env.ref('base.group_portal').id])]})
        with self.assertRaises(AccessError):
            self.worker.with_user(portal).action_check_in()

    def test_whatsapp_hidden_without_enterprise_app(self):
        entry = self.env['gate.entry'].create({'entry_type': 'visitor', 'visitor_name': 'X'})
        self.assertEqual(entry.whatsapp_available, 'whatsapp.composer' in self.env)
