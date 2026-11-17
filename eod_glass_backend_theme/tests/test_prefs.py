# -*- coding: utf-8 -*-
from odoo.exceptions import AccessError
from odoo.tests import TransactionCase, new_test_user, tagged


@tagged("post_install", "-at_install")
class TestOwnPreferences(TransactionCase):

    def test_user_changes_own_preferences(self):
        """The Core panel writes the preferences with the user's own rights."""
        user = new_test_user(self.env, login="aic_prefs_user", groups="base.group_user")
        me = user.with_user(user)
        me.write({"aic_nav": "mini", "aic_split": True, "aic_chatter": "bottom", "aic_m_tabbar": "hide"})
        self.assertEqual(me.read(["aic_nav", "aic_split"])[0]["aic_nav"], "mini")
        self.assertEqual(user._aic_prefs()["chatter"], "bottom")

    def test_not_someone_elses(self):
        user = new_test_user(self.env, login="aic_prefs_user", groups="base.group_user")
        other = new_test_user(self.env, login="aic_prefs_other", groups="base.group_user")
        with self.assertRaises(AccessError):
            other.with_user(user).write({"aic_nav": "side"})
