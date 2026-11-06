# -*- coding: utf-8 -*-
from odoo.tests import TransactionCase, tagged

from ..migrate_legacy import migrate_from_slate, rename


@tagged("post_install", "-at_install")
class TestMigrateLegacy(TransactionCase):
    """The pre-engine Slate data is renamed in place when Slate Suite is upgraded (aic_theme's pre_init_hook)."""

    def test_rename_rules(self):
        self.assertEqual(rename("slate_palette_mode"), "aic_palette_mode")
        self.assertEqual(rename("slate.focus"), "aic.focus")
        self.assertEqual(rename("model_slate_home"), "model_aic_home")
        self.assertEqual(rename("web_theme_slate.enabled"), "aic_theme.enabled")
        self.assertEqual(rename("slate_home.start_screen"), "aic_home.start_screen")
        self.assertEqual(rename("body.o_theme_slate { --slate-font: x }"), "body.o_aic_theme { --aic-font: x }")
        # words that merely contain the letters, and the bundle, are left alone
        self.assertEqual(rename("translate"), "translate")
        self.assertEqual(rename("field_ir_model_fields__translate"), "field_ir_model_fields__translate")
        self.assertEqual(rename("slate_suite"), "slate_suite")

    def test_nothing_to_do_on_an_engine_database(self):
        """A database that never had the old modules is left untouched."""
        self.assertFalse(migrate_from_slate(self.env.cr))
