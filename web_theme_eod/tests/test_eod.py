# -*- coding: utf-8 -*-
from odoo.tests import HttpCase, TransactionCase, tagged

from ..models import eod_palette
from odoo.addons.aic_theme.models import palette


@tagged("post_install", "-at_install")
class TestEodPalette(TransactionCase):

    def setUp(self):
        super().setUp()
        self.company = self.env.company
        # a known starting point: an upgraded database may have the colour-field tint switched off
        self.company.write({"aic_skin": "eod", "aic_glass_tint": True})

    def test_house_palette_is_empty(self):
        """Lagoon lives in the stylesheet: the house palette adds nothing to the page."""
        self.company.aic_palette_mode = "house"
        self.assertEqual(self.company.aic_palette_for("light"), "")
        self.assertEqual(self.company.aic_palette_for("dark"), "")

    def test_preset(self):
        self.company.write({"aic_palette_mode": "preset", "aic_palette_preset": "graphite"})
        css = self.company.aic_palette_for("light")
        self.assertTrue(css.startswith("body.o_aic_theme.o_aic_skin_eod {"))
        self.assertIn("--nm-brand: #18181B", css)
        self.assertIn("--gl-blob-a: #CFF3DF", css)
        # glass keeps its own surfaces: a palette never makes the panes opaque
        self.assertNotIn("--nm-surface", css)
        self.assertNotIn("--nm-well-bg", css)

    def test_presets_pass_aa(self):
        for name, roles in eod_palette.PRESETS.items():
            light, dark = roles["light"], roles["dark"]
            self.assertGreaterEqual(palette.contrast(light["act"], light["act_ink"]), 4.5, name)
            self.assertGreaterEqual(palette.contrast(light["link"], eod_palette.GROUND_LIGHT), 4.5, name)
            self.assertGreaterEqual(palette.contrast(light["hi"], light["hi_ink"]), 4.5, name)
            self.assertGreaterEqual(palette.contrast(dark["act"], dark["act_ink"]), 4.5, name)
            self.assertGreaterEqual(palette.contrast(dark["link"], eod_palette.GROUND_DARK), 4.5, name)

    def test_custom_tunes_against_the_pane(self):
        """Custom colours are tuned against the glass pane, and tint the field unless switched off."""
        self.company.write({"aic_palette_mode": "custom", "aic_color_action": "#C2185B", "aic_color_highlight": "#FCE4EC"})
        roles = self.company._aic_roles()
        self.assertGreaterEqual(palette.contrast(roles["light"]["link"], eod_palette.GROUND_LIGHT), 4.5)
        self.assertIn("--gl-blob-a", self.company.aic_palette_for("light"))
        self.company.aic_glass_tint = False
        self.assertNotIn("--gl-blob-a", self.company.aic_palette_for("light"))

    def test_slate_unchanged(self):
        """The same company on another look gets that look's palette CSS, not glass's."""
        if "slate" not in dict(self.company._fields["aic_skin"].selection):
            return
        self.company.write({"aic_skin": "slate", "aic_palette_mode": "custom", "aic_color_action": "#C2185B",
                            "aic_color_highlight": False, "aic_color_ink": False, "aic_keep_house_highlight": False})
        css = self.company.aic_palette_for("light")
        self.assertTrue(css.startswith("body.o_aic_theme {"))
        self.assertEqual(css, palette.palette_css(palette.derive_roles(action="#C2185B"), "light"))


@tagged("post_install", "-at_install")
class TestEodPage(HttpCase):

    def test_session_names_the_look(self):
        """Apps outside the web client (Point of Sale) learn the look from the session."""
        self.env.company.aic_skin = "eod"
        self.env["ir.config_parameter"].sudo().set_bool("aic_theme.enabled", True)
        self.authenticate("admin", "admin")
        self.assertIn('"aic_skin": "eod"', self.url_open("/odoo").text)

    def test_body_and_login(self):
        self.env.company.aic_skin = "eod"
        self.env["ir.config_parameter"].sudo().set_bool("aic_theme.enabled", True)
        res = self.url_open("/web/login")
        body = res.text[res.text.index("<body"):res.text.index(">", res.text.index("<body"))]
        self.assertIn("o_aic_skin_eod", body)
        self.authenticate("admin", "admin")
        html = self.url_open("/odoo").text
        body = html[html.index("<body"):html.index(">", html.index("<body"))]
        self.assertIn("o_aic_theme o_aic_skin_eod", body)
