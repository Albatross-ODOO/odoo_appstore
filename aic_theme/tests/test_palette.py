# -*- coding: utf-8 -*-
import io

from PIL import Image

from odoo.exceptions import ValidationError
from odoo.tests import HttpCase, TransactionCase, tagged
import base64

from odoo.addons.aic_theme.models import palette

SAMPLES = {
    "two-colour": [("#12355B", .5), ("#0E8C9A", .38), ("#7FD1D8", .12)],
    "warm": [("#C8553D", .52), ("#8AA17D", .3), ("#3B2A22", .18)],
    "yellow brand": [("#2B2B2B", .55), ("#E0A526", .45)],
    "green + blue": [("#2E9E5B", .6), ("#3BA3E0", .4)],
    "violet + pink": [("#6C3BF5", .62), ("#FF4F9A", .38)],
    "monochrome": [("#111111", 1.0)],
    "pale": [("#F7E8A4", .7), ("#DCE9F5", .3)],
}


def _png(*bands):
    """A logo made of vertical colour bands, as PNG bytes."""
    img = Image.new("RGBA", (120, 40), (255, 255, 255, 0))
    width = 120 // len(bands)
    for i, colour in enumerate(bands):
        for x in range(i * width, (i + 1) * width):
            for y in range(40):
                img.putpixel((x, y), palette.hex_to_rgb(colour) + (255,))
    out = io.BytesIO()
    img.save(out, "PNG")
    return out.getvalue()


@tagged("post_install", "-at_install")
class TestPaletteEngine(TransactionCase):

    def _assert_readable(self, roles, label):
        light, dark = roles["light"], roles["dark"]
        c = palette.contrast
        checks = {
            "action key": c(light["act"], light["act_ink"]),
            "highlight key": c(light["hi"], light["hi_ink"]),
            "link on white": c(light["link"], "#FFFFFF"),
            "muted on white": c(light["muted"], "#FFFFFF"),
            "ink on white": c(light["head"], "#FFFFFF"),
            "selected row": c(light["hi_soft_ink"], light["hi_soft"]),
            "dark action key": c(dark["act"], dark["act_ink"]),
            "dark link": c(dark["link"], dark["surface_high"]),
            "dark muted": c(dark["muted"], dark["surface_high"]),
        }
        for name, ratio in checks.items():
            self.assertGreaterEqual(ratio, 4.5, "%s: %s is %.2f:1" % (label, name, ratio))

    def test_house_palette_needs_no_override(self):
        roles = palette.derive_roles()
        self.assertFalse(roles["custom"])
        self.assertEqual(palette.palette_css(roles, "light"), "")
        self._assert_readable(roles, "house")

    def test_every_sample_is_readable(self):
        for label, colors in SAMPLES.items():
            for keep in (False, True):
                self._assert_readable(palette.derive_roles(colors=colors, keep_house_highlight=keep), label)

    def test_custom_colours_are_readable(self):
        for action in ("#FFFF00", "#00FF00", "#000080", "#FF00FF", "#808080"):
            self._assert_readable(palette.derive_roles(action=action, highlight="#00FFFF", ink="#FF0000"), action)

    def test_extract_from_image(self):
        image = Image.open(io.BytesIO(_png("#0E8C9A", "#0E8C9A", "#12355B")))
        colors = palette.extract_logo_colors(image)
        self.assertEqual(len(colors), 2)
        self.assertEqual(colors[0][0], "#0E8C9A")
        self.assertAlmostEqual(sum(s for _c, s in colors), 1.0, places=2)

    def test_extract_from_svg(self):
        # a traced logo: white backdrop, a big brand shape, a thin lighter edge, an accent; fills inherited, in
        # style and as rgb(); shapes inside <defs> are not drawn
        svg = b"""<?xml version="1.0"?><svg xmlns="http://www.w3.org/2000/svg" width="100" height="40">
            <path style="fill:#ffffff; stroke:none;" d="M0 0L100 0L100 40L0 40z"/>
            <g fill="#114FA3"><rect x="0" y="0" width="60" height="30"/></g>
            <path style="fill:#a7bedd" d="m60 0 h2 v30 h-2 z"/>
            <polygon fill="rgb(232, 76, 30)" points="70,0 100,0 100,20 70,20"/>
            <defs><rect fill="#00FF00" width="999" height="999"/></defs></svg>"""
        self.assertTrue(palette.is_svg(svg))
        self.assertFalse(palette.is_svg(_png("#0E8C9A", "#0E8C9A", "#12355B")))
        colors = palette.extract_svg_colors(svg)
        self.assertEqual([c for c, _s in colors], ["#114FA3", "#E84C1E"])   # the 2.4 % edge is under the cut
        self.assertAlmostEqual(colors[0][1], 1800 / 2460, places=3)

    def test_css_declares_roles(self):
        css = palette.palette_css(palette.derive_roles(colors=SAMPLES["two-colour"]), "dark")
        self.assertTrue(css.startswith("body.o_aic_theme {"))
        for token in ("--nm-brand:", "--nm-action:", "--nm-current:", "--nm-ink:", "--nm-surface:"):
            self.assertIn(token, css)
        self.assertNotIn("<", css)


@tagged("post_install", "-at_install")
class TestCompanyPalette(TransactionCase):

    def test_logo_mode(self):
        company = self.env.company
        company.logo = base64.b64encode(_png("#6C3BF5", "#6C3BF5", "#FF4F9A"))
        self.assertIn("#6C3BF5", company.aic_logo_colors)
        company.aic_palette_mode = "house"
        self.assertFalse(company.aic_palette_for("light"))
        company.aic_palette_mode = "logo"
        self.assertIn("--nm-brand: #6C3BF5", company.aic_palette_for("light"))
        # the dark palette re-declares the roles too (each look decides which surfaces it lets a palette change)
        self.assertIn("--nm-brand:", company.aic_palette_for("dark"))

    def test_custom_mode_and_validation(self):
        company = self.env.company
        company.write({"aic_palette_mode": "custom", "aic_color_action": "#0055AA"})
        self.assertIn("--nm-brand:", company.aic_palette_light)
        with self.assertRaises(ValidationError):
            company.aic_color_ink = "plum"

    def test_settings_preview(self):
        settings = self.env["res.config.settings"].create({"aic_palette_mode": "custom", "aic_color_action": "#0055AA"})
        self.assertIn("Action", settings.aic_palette_preview)
        self.assertIn("✓", settings.aic_palette_preview)

    def test_document_colours(self):
        company = self.env.company
        company.write({"aic_palette_mode": "custom", "aic_color_action": "#0055AA", "aic_color_ink": "#1B2A41"})
        light = company._aic_roles()["light"]
        settings = self.env["res.config.settings"].create({})
        action = settings.action_aic_apply_document_colors()
        self.assertEqual(action["tag"], "display_notification")
        self.assertEqual((company.primary_color, company.secondary_color), (light["head"], light["link"]))
        # documents print labels in the secondary colour: readable on white paper
        for color in (company.primary_color, company.secondary_color):
            self.assertGreaterEqual(palette.contrast(color, "#FFFFFF"), 4.5)
        if "email_secondary_color" in company._fields:
            self.assertEqual((company.email_secondary_color, company.email_primary_color), (light["act"], light["act_ink"]))
            self.assertGreaterEqual(palette.contrast(company.email_secondary_color, company.email_primary_color), 4.5)



@tagged("post_install", "-at_install")
class TestPaletteInPage(HttpCase):

    def test_webclient_has_company_palette(self):
        admin = self.env.ref("base.user_admin")
        admin.password = "aic-test-password"
        admin.company_id.aic_palette_mode = "house"
        self.authenticate("admin", "aic-test-password")
        page = self.url_open("/odoo").text
        self.assertNotIn('id="o_aic_palette"', page, "house palette: no override expected")
        admin.company_id.write({"aic_palette_mode": "custom", "aic_color_action": "#0055AA"})
        page = self.url_open("/odoo").text
        self.assertIn('id="o_aic_palette"', page)
        self.assertIn("--nm-brand:", page)
        self.assertIn("o_aic_theme", page)
