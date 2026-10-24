# -*- coding: utf-8 -*-
from odoo import models
from odoo.http import request

# The phone gantt extends and imports Enterprise's web_gantt, which lives in the on-demand bundle
# web.assets_backend_lazy. Community has that bundle too (Chart.js for graph views) but no
# web_gantt, so a manifest entry made every Community graph screen log "Missing (extension)
# parent templates: web_gantt.GanttController" (BUG-0048). These records exist only where
# web_gantt is installed; init() runs at every install / update of this module. The template is
# prepended so it is applied before any primary copy of web_gantt.GanttController.
GANTT_ASSETS = [
    {"name": "aic_workspace: phone gantt templates", "bundle": "web.assets_backend_lazy", "directive": "prepend",
     "path": "aic_workspace/static/src/mobile/gantt_phone.xml", "sequence": 20},
    {"name": "aic_workspace: phone gantt controller", "bundle": "web.assets_backend_lazy", "directive": "append",
     "path": "aic_workspace/static/src/mobile/gantt_phone.js", "sequence": 20},
    {"name": "aic_workspace: phone gantt styles", "bundle": "web.assets_backend_lazy", "directive": "append",
     "path": "aic_workspace/static/src/mobile/gantt_phone.scss", "sequence": 20},
    {"name": "aic_workspace: gantt legend template", "bundle": "web.assets_backend_lazy", "directive": "prepend",
     "path": "aic_workspace/static/src/views/gantt_legend.xml", "sequence": 21},
    {"name": "aic_workspace: gantt legend", "bundle": "web.assets_backend_lazy", "directive": "append",
     "path": "aic_workspace/static/src/views/gantt_legend.js", "sequence": 21},
    {"name": "aic_workspace: gantt legend styles", "bundle": "web.assets_backend_lazy", "directive": "append",
     "path": "aic_workspace/static/src/views/gantt_legend.scss", "sequence": 21},
]


class IrHttp(models.AbstractModel):
    _inherit = "ir.http"

    def session_info(self):
        info = super().session_info()
        if request.session.uid and not self.env.user._is_public():
            info["aic_prefs"] = self.env.user._aic_prefs()
            # "My profile" in the user menu (the phone's Me tab): only for a user linked to an employee
            info["aic_has_employee"] = bool("employee_id" in self.env.user._fields and self.env.user.employee_id)
        return info

    def webclient_rendering_context(self):
        # The installed app in the company's brand: the status bar takes the theme's ground for the
        # current scheme and iOS takes the logo as its home-screen icon (controllers/webmanifest.py
        # does the same for the manifest). Nothing changes while the Core theme is off.
        ctx = super().webclient_rendering_context()
        ctx["aic_app_theme_color"] = ctx["aic_app_touch_icon"] = False
        if self.env["res.config.settings"].sudo()._aic_theme_enabled():
            company = self.env.company.sudo()
            ctx["aic_app_theme_color"] = company._aic_app_theme_color(self.color_scheme())
            if company._aic_app_logo():
                ctx["aic_app_touch_icon"] = "/aic_workspace/app_icon/%s/any/180.png?v=%s" % (
                    company.id, company._aic_app_icon_version())
        return ctx

    def _aic_has_gantt(self):
        return bool(self.env["ir.module.module"].sudo().search_count(
            [("name", "=", "web_gantt"), ("state", "in", ("installed", "to upgrade", "to install"))]
        ))

    def init(self):
        super().init()
        Asset = self.env["ir.asset"].sudo()
        has_gantt = self._aic_has_gantt()
        for values in GANTT_ASSETS:
            record = Asset.search([("path", "=", values["path"])], limit=1)
            if has_gantt and not record:
                Asset.create(values)
            elif record and not has_gantt:
                record.unlink()
