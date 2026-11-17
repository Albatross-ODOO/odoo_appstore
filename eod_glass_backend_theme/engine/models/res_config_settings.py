# -*- coding: utf-8 -*-
import json

from markupsafe import Markup, escape

from odoo import api, fields, models

PARAM = "aic_theme.enabled"


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    aic_theme_enabled = fields.Boolean(
        string="Backend Theme Engine",
        config_parameter=PARAM,
        default=True,
        help="Apply the Core styling to the backend. "
             "Turning it off restores the standard Odoo look without uninstalling.",
    )
    aic_skin = fields.Selection(related="company_id.aic_skin", readonly=False)
    aic_skin_count = fields.Integer(compute="_compute_aic_skin_count")
    # per-company colours: stored on res.company, edited here
    aic_palette_mode = fields.Selection(related="company_id.aic_palette_mode", readonly=False)
    aic_app_icons = fields.Selection(related="company_id.aic_app_icons", readonly=False)
    aic_palette_preset = fields.Selection(related="company_id.aic_palette_preset", readonly=False)
    aic_keep_house_highlight = fields.Boolean(related="company_id.aic_keep_house_highlight", readonly=False)
    aic_color_action = fields.Char(related="company_id.aic_color_action", readonly=False)
    aic_color_highlight = fields.Char(related="company_id.aic_color_highlight", readonly=False)
    aic_color_ink = fields.Char(related="company_id.aic_color_ink", readonly=False)
    aic_palette_preview = fields.Html(compute="_compute_aic_palette_preview", sanitize=False)

    def action_aic_apply_document_colors(self):
        self.ensure_one()
        self.company_id.aic_apply_document_colors()
        return {"type": "ir.actions.client", "tag": "display_notification", "params": {
            "type": "success", "sticky": False,
            "message": self.env._("Documents and e-mails of %(company)s now use these colours.", company=self.company_id.name),
        }}

    def _compute_aic_skin_count(self):
        count = len(self.env["res.company"]._fields["aic_skin"].selection or [])
        for settings in self:
            settings.aic_skin_count = count

    @api.model
    def _aic_theme_enabled(self):
        # a boolean setting is stored as "True" / "False"; a database that has never saved the settings
        # has no parameter yet, and the theme is on (the field default)
        value = self.env["ir.config_parameter"].sudo().get_param(PARAM, "True")
        # the engine has no look of its own: without an installed skin the theme stays off
        return bool(str(value).strip().lower() not in ("false", "0", "")
                    and self.env.company.sudo()._aic_effective_skin())

    @api.depends("company_id", "aic_skin", "aic_palette_mode", "aic_palette_preset", "aic_keep_house_highlight",
                 "aic_color_action", "aic_color_highlight", "aic_color_ink")
    def _compute_aic_palette_preview(self):
        for settings in self:
            company = settings.company_id
            if not company:
                settings.aic_palette_preview = False
                continue
            # preview what is on screen, before it is saved: a virtual company with these values
            probe = company.new({
                "aic_skin": settings.aic_skin,
                "aic_palette_mode": settings.aic_palette_mode or "house",
                "aic_palette_preset": settings.aic_palette_preset,
                "aic_keep_house_highlight": settings.aic_keep_house_highlight,
                "aic_color_action": settings.aic_color_action,
                "aic_color_highlight": settings.aic_color_highlight,
                "aic_color_ink": settings.aic_color_ink,
                "aic_logo_colors": company.aic_logo_colors,
            })
            settings.aic_palette_preview = self._aic_render_preview(
                probe.aic_preview_roles(), company.aic_logo_colors)

    @api.model
    def _aic_render_preview(self, rows, logo_colors):
        def chip(bg, fg, ratio):
            return Markup(
                '<span style="display:inline-flex;align-items:center;gap:8px;padding:6px 10px;border-radius:10px;'
                'background:%s;color:%s;font-weight:600;box-shadow:inset 0 0 0 1px rgba(0,0,0,.08)">Aa '
                '<small style="font-weight:700">%s:1 %s</small></span>'
            ) % (bg, fg, "%.1f" % ratio, "✓" if ratio >= 4.5 else "✗")

        out = [Markup('<table class="o_aic_palette_preview" style="border-collapse:separate;border-spacing:0 6px">'
                      '<tr><th></th><th style="padding:0 12px 0 0">%s</th><th>%s</th></tr>')
               % (self.env._("Light"), self.env._("Dark"))]
        labels = {
            "Action": self.env._("Action"), "Highlight": self.env._("Highlight"), "Ink": self.env._("Ink"),
            "Link": self.env._("Link"), "Muted text": self.env._("Muted text"),
        }
        for name, lbg, lfg, lr, dbg, dfg, dr in rows:
            out.append(Markup('<tr><td style="padding-right:12px;font-weight:600">%s</td>'
                              '<td style="padding-right:12px">%s</td><td>%s</td></tr>')
                       % (labels.get(name, name), chip(lbg, lfg, lr), chip(dbg, dfg, dr)))
        out.append(Markup("</table>"))
        try:
            found = json.loads(logo_colors or "[]")
        except ValueError:
            found = []
        if found:
            swatches = Markup("").join(
                Markup('<span title="%s · %s%%" style="display:inline-block;width:22px;height:22px;border-radius:7px;'
                       'margin-right:6px;background:%s;box-shadow:inset 0 0 0 1px rgba(0,0,0,.1)"></span>')
                % (c, round(s * 100), c) for c, s in found)
            out.append(Markup('<div style="margin-top:6px;font-size:12px">%s %s</div>')
                       % (self.env._("Found in the logo:"), swatches))
        return Markup("").join(out)
