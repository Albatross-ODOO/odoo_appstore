# -*- coding: utf-8 -*-
from odoo.tests import HttpCase, tagged


@tagged("post_install", "-at_install")
class TestLoginPage(HttpCase):
    """The sign-in page takes the Core look only while the look is on (phase 54)."""

    def _body_classes(self):
        res = self.url_open("/web/login")
        self.assertEqual(res.status_code, 200)
        html = res.text
        start = html.index("<body")
        return html[start:html.index(">", start)]

    def test_on_and_off(self):
        param = self.env["ir.config_parameter"].sudo()
        param.set_bool("aic_theme.enabled", True)
        if not self.env.company._aic_effective_skin():
            # the engine alone has no look: the page stays stock Odoo until a look is installed
            self.assertNotIn("o_aic_login", self._body_classes())
            return
        self.assertIn("o_aic_login", self._body_classes())
        param.set_bool("aic_theme.enabled", False)
        self.assertNotIn("o_aic_login", self._body_classes())
