from datetime import timedelta

from odoo import fields
from odoo.tests import HttpCase, tagged


@tagged('post_install', '-at_install')
class TestGateDeskUI(HttpCase):
    browser_size = '1400,900'

    def test_guard_tour(self):
        guard = self.env['res.users'].create({
            'name': 'Guard Tour', 'login': 'guard_tour', 'password': 'guard_tour',
            'group_ids': [(6, 0, [self.env.ref('base.group_user').id, self.env.ref('gate_management.group_gate_guard').id])],
        })
        self.env['gate.worker'].create({'name': 'Rakesh Patel', 'worker_code': 'TOUR042', 'mobile': '9879022314'})
        start = fields.Datetime.now() + timedelta(hours=1)
        entry = self.env['gate.entry'].create({
            'entry_type': 'visitor', 'visitor_name': 'Meera Joshi', 'mobile_number': '9824177390',
            'scheduled_start': start, 'scheduled_end': start + timedelta(hours=2), 'host_id': guard.id,
        })
        entry.action_schedule()
        entry.otp = '482917'
        self.start_tour("/odoo/action-gate_management.action_gate_desk_home", "gate_desk_tour", login="guard_tour")
