# -*- coding: utf-8 -*-
from unittest.mock import patch

from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestLock(TransactionCase):
    """Workspace is sold with a look: its web client files are only served while a look is installed."""

    def _rules(self):
        return self.env["ir.asset"].with_context(active_test=False).search([("name", "=like", "aic_lock: Workspace%")])

    def test_rules_follow_the_look(self):
        Company = type(self.env["res.company"])
        self.assertEqual(len(self._rules()), 2)
        with patch.object(Company, "_aic_look_installed", return_value=False):
            self.env["ir.asset"]._aic_sync_lock()
            self.assertTrue(all(self._rules().mapped("active")), "no look: Workspace's files are taken out")
            paths = self.env["ir.asset"]._get_asset_paths("web.assets_backend", {})
            self.assertFalse([p for p, *_ in paths if p.startswith("/aic_workspace/static/src/") or p.startswith("aic_workspace/static/src/")])
        with patch.object(Company, "_aic_look_installed", return_value=True):
            self.env["ir.asset"]._aic_sync_lock()
            self.assertFalse(any(self._rules().mapped("active")), "a look installed: Workspace is served")
            paths = self.env["ir.asset"]._get_asset_paths("web.assets_backend", {})
            self.assertTrue([p for p, *_ in paths if "aic_workspace/static/src/" in p])
