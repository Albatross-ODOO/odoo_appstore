# -*- coding: utf-8 -*-
from odoo.tests import TransactionCase, new_test_user, tagged


@tagged("post_install", "-at_install")
class TestMyProfile(TransactionCase):

    def test_my_profile_opens_own_employee(self):
        """My profile opens the user's own employee record; without one, Odoo's preferences sheet."""
        user = new_test_user(self.env, login="aic_profile_user", groups="base.group_user")
        if "hr.employee" not in self.env:
            action = self.env["res.users"].with_user(user).aic_my_profile_action()
            self.assertEqual(action.get("res_model"), "res.users")
            return
        self.env["hr.employee"].search([("user_id", "=", user.id)]).unlink()
        action = self.env["res.users"].with_user(user).aic_my_profile_action()
        self.assertEqual(action.get("res_model"), "res.users")
        employee = self.env["hr.employee"].create({"name": "Core Profile", "user_id": user.id})
        action = self.env["res.users"].with_user(user).aic_my_profile_action()
        self.assertEqual((action["res_model"], action["res_id"]), ("hr.employee.public", employee.id))
        # what the user is sent to can be read by the user
        self.env[action["res_model"]].with_user(user).browse(action["res_id"]).read(["name"])
        user.group_ids |= self.env.ref("hr.group_hr_user")
        action = self.env["res.users"].with_user(user).aic_my_profile_action()
        self.assertEqual(action["res_model"], "hr.employee")
