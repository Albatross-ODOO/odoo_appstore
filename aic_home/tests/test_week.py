# -*- coding: utf-8 -*-
import json
from datetime import timedelta

from odoo import fields
from odoo.tests import TransactionCase, new_test_user, tagged


@tagged("post_install", "-at_install")
class TestMyWeek(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = new_test_user(cls.env, login="aic_week_user", groups="base.group_user,base.group_partner_manager")
        cls.mate = new_test_user(cls.env, login="aic_week_mate", groups="base.group_user")
        cls.doc = cls.env["res.partner"].create({"name": "Week Document"})
        cls.todo = cls.env.ref("mail.mail_activity_data_todo")

    def _activity(self, user, days, summary="Call back"):
        return self.env["mail.activity"].create({
            "res_model_id": self.env["ir.model"]._get_id("res.partner"), "res_id": self.doc.id,
            "activity_type_id": self.todo.id, "user_id": user.id, "summary": summary,
            "date_deadline": fields.Date.context_today(self.env["aic.home"]) + timedelta(days=days),
        })

    def _week(self, user):
        return self.env["aic.home"].with_user(user).get_week_data()

    def test_shape_and_done_today(self):
        before = self._week(self.user)
        self.assertEqual(len(before["days"]), 7)
        self.assertEqual(sum(d["is_today"] for d in before["days"]), 1)
        json.dumps(before, default=str)
        activity = self._activity(self.user, 0)
        activity.with_user(self.user).action_feedback(feedback="done")
        after = self._week(self.user)
        self.assertEqual(after["done"], before["done"] + 1, "marking an activity done counts for the person who did it")
        today = next(d for d in after["days"] if d["is_today"])
        self.assertGreaterEqual(today["done"], 1)
        self.assertIn(str(after["done"]), after["summary"])

    def test_overdue_and_still_due(self):
        self._activity(self.user, -3)
        data = self._week(self.user)
        self.assertGreaterEqual(data["overdue"], 1)
        self.assertEqual(data["overdue_action"]["res_model"], "mail.activity")
        if data["overdue"] == 1:
            self.assertIn("1 is overdue.", data["summary"], "one is singular")

    def test_week_starts_on_the_language_first_day(self):
        lang = self.env["res.lang"]._lang_get(self.env.lang or "en_US")
        first = int(lang.week_start or 1)
        bounds = self.env["aic.home"]._aic_week_bounds(fields.Date.today())
        self.assertEqual(bounds["start"].isoweekday(), first)
        self.assertEqual((bounds["end"] - bounds["start"]).days, 7)

    def test_no_team_for_a_plain_user(self):
        self.assertIsNone(self._week(self.user)["team"])

    def test_team_for_a_sales_team_leader(self):
        if "crm.team" not in self.env:
            self.skipTest("sales teams are not installed")
        self.env["crm.team"].create({"name": "Week Team", "user_id": self.user.id, "member_ids": [(6, 0, [self.mate.id])]})
        self._activity(self.mate, -2)
        team = self._week(self.user)["team"]
        self.assertTrue(team)
        row = next(m for m in team["members"] if m["id"] == self.mate.id)
        self.assertGreaterEqual(row["overdue"], 1)
        self.assertNotIn(self.user.id, [m["id"] for m in team["members"]], "the lead is not in their own table")
        names = [m["name"].lower() for m in team["members"]]
        self.assertEqual(names, sorted(names), "alphabetical, never ranked")
