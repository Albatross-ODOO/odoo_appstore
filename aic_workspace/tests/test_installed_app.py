# -*- coding: utf-8 -*-
import io

from PIL import Image

from odoo.tests import HttpCase, tagged
from odoo.tools import BinaryBytes


def _logo():
    """A wide two-colour logo on a transparent ground, as PNG bytes."""
    img = Image.new("RGBA", (300, 100), (255, 255, 255, 0))
    for x in range(40, 260):
        for y in range(30, 70):
            img.putpixel((x, y), (108, 59, 245, 255) if x < 150 else (255, 79, 154, 255))
    out = io.BytesIO()
    img.save(out, "PNG")
    return out.getvalue()


@tagged("post_install", "-at_install")
class TestInstalledApp(HttpCase):

    def setUp(self):
        super().setUp()
        self.admin = self.env.ref("base.user_admin")
        self.admin.password = "aic-test-password"
        self.company = self.admin.company_id
        self.company.name = "Acme Fittings"
        self.env["ir.config_parameter"].sudo().set_str("web.web_app_name", "Odoo")
        self.env["ir.config_parameter"].sudo().set_bool("aic_theme.enabled", True)
        # the light scheme: the dark one has its own window colour (Enterprise keeps it per user)
        if "res.users.settings" in self.env and "color_scheme" in self.env["res.users.settings"]._fields:
            self.env["res.users.settings"]._find_or_create_for_user(self.admin).color_scheme = "light"

    def _manifest(self):
        return self.url_open("/web/manifest.webmanifest").json()

    def test_manifest_in_company_brand(self):
        self.company.logo = BinaryBytes(_logo())
        self.authenticate("admin", "aic-test-password")
        manifest = self._manifest()
        self.assertEqual(manifest["name"], "Acme Fittings")
        self.assertEqual(manifest["short_name"], "Acme")
        window = self.company._aic_window_color("light")    # the look's ground (white for Slate)
        self.assertEqual(manifest["theme_color"], window)
        self.assertEqual(manifest["background_color"], window)
        purposes = sorted((icon["sizes"], icon["purpose"]) for icon in manifest["icons"])
        self.assertEqual(purposes, [("192x192", "any"), ("512x512", "any"), ("512x512", "maskable")])
        if "aic_home" in self.env.registry._init_modules:
            self.assertEqual([s["url"] for s in manifest["shortcuts"][:2]], ["/odoo/today", "/odoo/focus"])

        # the icons are square PNGs of the announced size, the logo centred on white
        for icon in manifest["icons"]:
            response = self.url_open(icon["src"])
            self.assertEqual(response.headers["Content-Type"], "image/png")
            image = Image.open(io.BytesIO(response.content))
            size = int(icon["sizes"].split("x")[0])
            self.assertEqual(image.size, (size, size))
            self.assertEqual(image.convert("RGB").getpixel((2, 2)), (255, 255, 255))
            self.assertNotEqual(image.convert("RGB").getpixel((size // 2 - 4, size // 2)), (255, 255, 255))

        # the page head: white status bar, the logo as the iOS icon
        page = self.url_open("/odoo").text
        self.assertIn('name="theme-color" content="%s"' % window, page)
        self.assertIn("/aic_workspace/app_icon/%s/any/180.png" % self.company.id, page)

        # the start-up splash shows the same icon on the window colour
        self.assertIn('class="o_aic_splash"', page)
        self.assertIn("background: %s" % window, page)

        # the offline page wears the brand too
        offline = self.url_open("/odoo/offline").text
        self.assertIn("Acme Fittings opens again", offline)

    def test_admin_app_name_wins(self):
        self.env["ir.config_parameter"].sudo().set_str("web.web_app_name", "Acme Field")
        self.authenticate("admin", "aic-test-password")
        self.assertEqual(self._manifest()["name"], "Acme Field")

    def test_no_logo_keeps_odoo_icons(self):
        self.company.logo = False
        self.authenticate("admin", "aic-test-password")
        manifest = self._manifest()
        self.assertTrue(all(icon["src"].startswith("/web/static/img/odoo-icon") for icon in manifest["icons"]))
        self.assertEqual(manifest["name"], "Acme Fittings")

    def test_theme_off_is_stock_odoo(self):
        self.company.logo = BinaryBytes(_logo())
        self.env["ir.config_parameter"].sudo().set_bool("aic_theme.enabled", False)
        self.authenticate("admin", "aic-test-password")
        manifest = self._manifest()
        self.assertEqual(manifest["name"], "Odoo")
        self.assertEqual(manifest["theme_color"], "#714B67")
        page = self.url_open("/odoo").text
        self.assertIn('name="theme-color" content="#71639e"', page)
        self.assertIn("/web/static/img/odoo-icon-ios.png", page)

    def test_no_splash_with_the_look_off(self):
        self.env["ir.config_parameter"].sudo().set_bool("aic_theme.enabled", False)
        self.authenticate("admin", "aic-test-password")
        self.assertNotIn("o_aic_splash", self.url_open("/odoo").text)
