# -*- coding: utf-8 -*-
from odoo import models
from odoo.http import request

PARAM = "aic_theme.enabled"

# Community dark mode: Odoo Community has no dark colour scheme (web_enterprise ships the dark
# variables, the switch and the cookie handling). The theme fills the gap with its own dark
# palette (community_dark.scss), compiled into web.assets_web_dark BEFORE Odoo's primary
# variables, and honours the same `color_scheme` cookie Enterprise uses — only when
# web_enterprise is not installed, so an Enterprise database is never touched.
# The same pair goes into the lazily loaded dark bundle (graph, pivot — and gantt, grid, map… where
# installed), compiled on its own: without it those views came out with the light palette.
COMMUNITY_DARK_ASSETS = [
    {
        "name": "aic_theme: community dark variables",
        "bundle": bundle,
        "directive": "before",
        "target": "web/static/src/scss/primary_variables.scss",
        "path": "aic_theme/static/src/scss/community_dark.scss",
        "sequence": 20,     # after the bundle's own `include` (manifest lines count as 16)
    }
    for bundle in ("web.assets_web_dark", "web.assets_backend_lazy_dark")
] + [
    {
        # Bootstrap's tint/shade swapped for a dark ground (emphasis inks, subtle grounds)
        "name": "aic_theme: community dark colour functions",
        "bundle": bundle,
        "directive": "after",
        "target": "web/static/lib/bootstrap/scss/_functions.scss",
        "path": "aic_theme/static/src/scss/community_dark_functions.scss",
        "sequence": 20,
    }
    for bundle in ("web.assets_web_dark", "web.assets_backend_lazy_dark")
]


# Enterprise dark mode (Odoo 19 only): Odoo 19 Enterprise draws its dark mode with blue-navy greys; Core 4 was
# designed on the neutral charcoal of Odoo 20 (enterprise_dark.scss). The file is PREPENDED to the dark bundles
# (no target, so a bundle never breaks if web_enterprise goes away) of Enterprise databases only.
# point_of_sale.assets_prod_dark is built only when the POS is installed.
ENTERPRISE_DARK_ASSETS = [
    {
        "name": "aic_theme: enterprise dark greys",
        "bundle": bundle,
        "directive": "prepend",
        "path": "aic_theme/static/src/scss/enterprise_dark.scss",
        "sequence": 20,
    }
    for bundle in ("web.assets_web_dark", "web.assets_backend_lazy_dark", "point_of_sale.assets_prod_dark")
]


class IrHttp(models.AbstractModel):
    _inherit = "ir.http"

    def _aic_is_community(self):
        return "web_enterprise" not in self.env.registry._init_modules

    def webclient_rendering_context(self):
        # Adds one boolean to the qcontext of ``web.webclient_bootstrap`` so the
        # template can put ``o_aic_theme`` on <body>. Evaluated once per page load
        # (the bootstrap page is ``Cache-Control: no-store``), no extra RPC, no JS.
        ctx = super().webclient_rendering_context()
        ctx["aic_theme_enabled"] = self.env["res.config.settings"]._aic_theme_enabled()
        # `o_aic_community` on <body>: the Community-only readability rules (community.scss)
        # hang on it, so an Enterprise page is never affected by them
        ctx["aic_community"] = self._aic_is_community()
        # Per-company colours: a few CSS custom properties for the current company and colour
        # scheme, precomputed and stored on res.company (empty for the house palette, so most
        # databases get nothing extra).
        ctx["aic_palette_css"] = ""
        ctx["aic_skin"] = False
        if ctx["aic_theme_enabled"]:
            company = self.env.company.sudo()
            ctx["aic_skin"] = company._aic_effective_skin()
            ctx["aic_palette_css"] = company.aic_palette_for(self.color_scheme())
        return ctx

    def session_info(self):
        # the look in use, for the apps outside the web client that read the session (Point of Sale: pos_skin.js)
        info = super().session_info()
        enabled = self.env["res.config.settings"].sudo()._aic_theme_enabled() if self.env.uid else False
        info["aic_skin"] = self.env.company.sudo()._aic_effective_skin() if enabled else False
        info["aic_app_icons"] = self.env.company.sudo().aic_app_icons if enabled else False
        return info

    def color_scheme(self):
        # Community: Odoo answers "light" whatever the cookie says; read the cookie the way
        # web_enterprise does. Enterprise: untouched (super() is web_enterprise's own logic).
        scheme = super().color_scheme()
        if scheme == "light" and self._aic_is_community() and request:
            if request.httprequest.cookies.get("color_scheme") == "dark":
                return "dark"
        return scheme

    def init(self):
        # Runs at every install / update of the module: keep exactly one ir.asset record per bundle for
        # the edition's dark palette: the Community dark variables when web_enterprise is absent, the
        # Enterprise charcoal greys when it is present.
        super().init()
        Asset = self.env["ir.asset"].sudo()
        community = self._aic_is_community()
        wanted = [(values, community) for values in COMMUNITY_DARK_ASSETS]
        wanted += [(values, not community) for values in ENTERPRISE_DARK_ASSETS]
        for values, keep in wanted:
            record = Asset.search([("path", "=", values["path"]), ("bundle", "=", values["bundle"])], limit=1)
            if keep and not record:
                Asset.create(values)
            elif record and not keep:
                record.unlink()
