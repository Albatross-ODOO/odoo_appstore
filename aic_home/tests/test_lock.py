# -*- coding: utf-8 -*-
from unittest.mock import patch

from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestLock(TransactionCase):
    """Home is sold with a look: without one its menu and landing page disappear with its web client."""

    def test_home_needs_a_look(self):
        Company = type(self.env["res.company"])
        home = self.env.ref("aic_home.menu_aic_home_root")
        action = self.env.ref("aic_home.action_aic_home")
        with patch.object(Company, "_aic_look_installed", return_value=True):
            self.assertIn(home.id, self.env["ir.ui.menu"]._visible_menu_ids())
            self.assertEqual(self.env["ir.http"]._aic_home_start_action(), action)
        with patch.object(Company, "_aic_look_installed", return_value=False):
            self.assertNotIn(home.id, self.env["ir.ui.menu"]._visible_menu_ids())
            self.assertFalse(self.env["ir.http"]._aic_home_start_action())
            self.env["ir.asset"]._aic_sync_lock()
            rule = self.env.ref("aic_home.lock_assets_backend")
            self.assertTrue(rule.active)
        with patch.object(Company, "_aic_look_installed", return_value=True):
            self.env["ir.asset"]._aic_sync_lock()
            self.assertFalse(self.env.ref("aic_home.lock_assets_backend").active)
