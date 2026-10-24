# -*- coding: utf-8 -*-
from odoo.tests import TransactionCase, new_test_user, tagged


@tagged("post_install", "-at_install")
class TestHeaderCompact(TransactionCase):

    def test_on_by_default_and_user_writeable(self):
        """The compact record header is on for everyone, and a user can turn it off for themselves."""
        user = new_test_user(self.env, login="aic_header_user", groups="base.group_user")
        self.assertTrue(user._aic_prefs()["header_compact"])
        user.with_user(user).write({"aic_header_compact": False})
        self.assertFalse(user._aic_prefs()["header_compact"])


@tagged("post_install", "-at_install")
class TestDensityAndNotifications(TransactionCase):

    def test_user_sets_density_and_notification_channel(self):
        """Density and Odoo's notification channel are the user's own choices, written with their own rights."""
        user = new_test_user(self.env, login="aic_density_user", groups="base.group_user")
        prefs = user._aic_prefs()
        self.assertEqual(prefs["density"], "comfortable")
        self.assertIn(prefs["notify"], ("email", "inbox"))
        user.with_user(user).write({"aic_density": "compact", "notification_type": "inbox"})
        prefs = user._aic_prefs()
        self.assertEqual(prefs["density"], "compact")
        self.assertEqual(prefs["notify"], "inbox")

    def test_user_sets_transparency(self):
        """Transparency is the user's own choice too (EOD reads it; other looks ignore it)."""
        user = new_test_user(self.env, login="aic_glass_user", groups="base.group_user")
        self.assertEqual(user._aic_prefs()["transparency"], "full")
        user.with_user(user).write({"aic_transparency": "reduce"})
        self.assertEqual(user._aic_prefs()["transparency"], "reduce")

    def test_portal_users_have_no_channel_choice(self):
        portal = new_test_user(self.env, login="aic_density_portal", groups="base.group_portal")
        self.assertFalse(portal._aic_prefs()["notify"])
