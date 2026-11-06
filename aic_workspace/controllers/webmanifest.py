# -*- coding: utf-8 -*-
"""The installed app in the company's brand (see models/res_company.py).

With the Core theme on, Odoo's manifest gets the company's name, its logo as the icons, the theme's
white ground for the window and splash, and Home / Focus shortcuts (Home). Everything else
(scope, share target, the shortcuts other apps add, the service worker) stays Odoo's own.
"""
import re

from odoo import http
from odoo.addons.web.controllers import webmanifest
from odoo.http import request
from odoo.tools import BinaryBytes


def _branded_company():
    """The company whose brand the app wears, or None when Core is off or the company has no logo."""
    if not request.env["res.config.settings"].sudo()._aic_theme_enabled():
        return None
    company = request.env.company.sudo()
    return company if company._aic_app_logo() else None


def _short_name(name, limit=12):
    """The name under the home-screen icon: no bracketed part, whole words up to ``limit`` characters."""
    words = re.sub(r"\s*\(.*?\)", "", name).split() or name.split()
    short = words[0][:limit] if words else name[:limit]
    for word in words[1:]:
        if len(short) + 1 + len(word) > limit:
            break
        short += " " + word
    return short


def _icon_url(company, size, purpose="any"):
    return "/aic_workspace/app_icon/%s/%s/%s.png?v=%s" % (
        company.id, purpose, size, company._aic_app_icon_version())


class WebManifest(webmanifest.WebManifest):

    def _get_webmanifest(self):
        manifest = super()._get_webmanifest()
        if not request.env["res.config.settings"].sudo()._aic_theme_enabled():
            return manifest
        company = request.env.company.sudo()
        name = company._aic_app_name()
        manifest.update({
            "name": name,
            "short_name": _short_name(name),
            "background_color": company._aic_app_theme_color("light"),
            "theme_color": company._aic_app_theme_color("light"),
        })
        if company._aic_app_logo():
            manifest["icons"] = [
                {"src": _icon_url(company, 192), "sizes": "192x192", "type": "image/png", "purpose": "any"},
                {"src": _icon_url(company, 512), "sizes": "512x512", "type": "image/png", "purpose": "any"},
                {"src": _icon_url(company, 512, "maskable"), "sizes": "512x512", "type": "image/png",
                 "purpose": "maskable"},
            ]
        manifest["shortcuts"] = self._aic_shortcuts(company) + manifest.get("shortcuts", [])
        return manifest

    def _aic_shortcuts(self, company):
        """Home and the Focus queue first, when Home is installed and the user is signed in."""
        if "aic_home" not in request.env.registry._init_modules or not request.env.user._is_internal():
            return []
        icon = ([{"src": _icon_url(company, 192), "sizes": "192x192", "type": "image/png"}]
                if company._aic_app_logo() else [])
        return [
            {"name": request.env._("Home"), "url": "/odoo/today", "description": request.env._("Today's agenda and your apps"), "icons": icon},
            {"name": request.env._("Focus queue"), "url": "/odoo/focus", "description": request.env._("Work through your due activities"),
             "icons": icon},
        ]

    @http.route("/aic_workspace/app_icon/<int:company_id>/<string:purpose>/<int:size>.png",
                type="http", auth="public", methods=["GET"], readonly=True)
    def aic_app_icon(self, company_id, purpose, size, **kwargs):
        company = request.env["res.company"].sudo().browse(company_id).exists()
        image = company._aic_app_icon(size, purpose) if company else None
        if not image:
            return request.redirect("/web/static/img/odoo-icon-192x192.png")
        # the URL carries the logo's version, so the icon can be cached for long
        return request.make_response(image, headers=[
            ("Content-Type", "image/png"), ("Cache-Control", "public, max-age=604800"),
        ])

    @http.route()
    def offline(self):
        company = _branded_company()
        if not company:
            return super().offline()
        light = company._aic_roles()["light"]
        return request.render("web.webclient_offline", {
            "odoo_icon": BinaryBytes(company._aic_app_icon(192)),
            "aic_app_name": company._aic_app_name(),
            "aic_offline_text": request.env._(
                "Check your network connection. %(app)s opens again as soon as you are back online.",
                app=company._aic_app_name()),
            "aic_app_action": light["act"],
            "aic_app_action_ink": light["act_ink"],
        })
