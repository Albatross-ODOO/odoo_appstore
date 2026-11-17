# -*- coding: utf-8 -*-
from datetime import timedelta

from odoo import fields
from odoo.tests import TransactionCase, new_test_user, tagged


@tagged("post_install", "-at_install")
class TestTeamOverdue(TransactionCase):
    """Home's Missed card links the manager to the team's overdue activities."""

    def setUp(self):
        super().setUp()
        if "crm.team" not in self.env and "hr.employee" not in self.env:
            self.skipTest("needs Sales teams or Employees")
        self.lead = new_test_user(self.env, "aic_lead", groups="base.group_user,base.group_partner_manager")
        self.member = new_test_user(self.env, "aic_member", groups="base.group_user")
        self.other = new_test_user(self.env, "aic_other", groups="base.group_user")
        if "crm.team" in self.env:
            self.env["crm.team"].create({"name": "Core team", "user_id": self.lead.id, "member_ids": [(6, 0, [self.member.id])]})
        else:
            boss = self.env["hr.employee"].create({"name": "Boss", "user_id": self.lead.id})
            self.env["hr.employee"].create({"name": "Member", "user_id": self.member.id, "parent_id": boss.id})
        partner = self.env["res.partner"].create({"name": "Core overdue"})
        late = fields.Date.today() - timedelta(days=3)
        todo = self.env.ref("mail.mail_activity_data_todo")
        for user in (self.member, self.member, self.other, self.lead):
            partner.activity_schedule(activity_type_id=todo.id, user_id=user.id, date_deadline=late)

    def test_team_users(self):
        team = self.env["aic.home"].with_user(self.lead)._aic_team_users()
        self.assertIn(self.member, team)
        self.assertNotIn(self.lead, team)
        self.assertNotIn(self.other, team)

    def test_counts_and_action(self):
        Home = self.env["aic.home"].with_user(self.lead)
        data = Home.get_home_data()
        self.assertEqual(data["missed_count"], 1)
        self.assertEqual(data["team_overdue_count"], 2)
        action = Home.action_overdue("team")
        self.assertEqual(action["res_model"], "mail.activity")
        self.assertEqual(action["context"], {"group_by": ["user_id"]})
        found = self.env["mail.activity"].with_user(self.lead).search(action["domain"])
        self.assertEqual(set(found.user_id.ids), {self.member.id})
        mine = self.env["mail.activity"].search(Home.action_overdue("mine")["domain"])
        self.assertEqual(mine.user_id, self.lead)

    def test_no_team(self):
        data = self.env["aic.home"].with_user(self.other).get_home_data()
        self.assertEqual(data["team_overdue_count"], 0)
