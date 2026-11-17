# -*- coding: utf-8 -*-
from odoo.tests import HttpCase, TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestStylesCompile(TransactionCase):
    """Every Core stylesheet must compile: libsass refuses some modern CSS (min() with mixed units,
    color-mix() unless quoted), and Odoo then falls back to the previous styles with a red banner instead
    of failing loudly. Covers every module installed with the theme (workspace, Home, Share on WhatsApp)."""

    def _assert_compiles(self, bundle_name):
        bundle = self.env["ir.qweb"]._get_asset_bundle(bundle_name, js=False)
        bundle.preprocess_css()
        self.assertFalse(bundle.css_errors, "%s failed to compile:\n%s" % (bundle_name, "\n".join(bundle.css_errors)))

    def test_backend_light(self):
        self._assert_compiles("web.assets_web")

    def test_backend_dark(self):
        self._assert_compiles("web.assets_web_dark")


@tagged("post_install", "-at_install")
class TestWebClientStarts(HttpCase):
    """The backend must start in a real browser with no JavaScript error: a syntax error in any Core
    script stops the whole client, and only a browser notices it. Desktop and phone sizes."""

    def test_desktop(self):
        self.browser_js("/odoo", "console.log('test successful')", ready="odoo.isReady", login="admin", timeout=120)

    def test_phone(self):
        self.browser_size = "390x844"
        self.touch_enabled = True
        self.browser_js("/odoo", "console.log('test successful')", ready="odoo.isReady", login="admin", timeout=120)
