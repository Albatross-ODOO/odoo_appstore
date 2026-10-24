# -*- coding: utf-8 -*-
import base64
import json
import logging

from odoo import api, fields, models
from odoo.tools.image import ImageProcess
from odoo.exceptions import ValidationError

from . import palette

_logger = logging.getLogger(__name__)

PALETTE_MODES = [
    ("house", "House colours"),
    ("logo", "From the company logo"),
    ("custom", "Custom colours"),
]


SKIN_PARAM = "aic_theme.default_skin"


class ResCompany(models.Model):
    _inherit = "res.company"

    # The look ("skin") this company's users see. The engine ships no look of its own: each skin
    # module (web_theme_slate, web_theme_eod, ...) adds its value with selection_add and its own
    # stylesheet scoped to body.o_aic_skin_<value>. No skin installed: the theme stays off.
    aic_skin = fields.Selection(
        [], string="Look",
        help="The look of the backend for this company's users. Each installed theme adds one.")

    aic_palette_mode = fields.Selection(
        PALETTE_MODES, string="Theme colours", default="house", required=True,
        help="House colours: the look's own colours.\n"
             "From the company logo: the logo's main colours, adjusted until every text is readable.\n"
             "Custom colours: pick the action, highlight and ink colours yourself.")
    # Ready-made palettes: a look that has some adds a "preset" palette mode and its palettes here
    # (selection_add), with their role colours in _aic_preset_roles().
    aic_palette_preset = fields.Selection([], string="Palette")
    aic_keep_house_highlight = fields.Boolean(
        string="Keep the house highlight",
        help="Use the brand colour for actions and ink, but keep the look's own highlight for "
             "\"you are here\" (current stage, active app, selected row).")
    aic_color_action = fields.Char(string="Action colour", help="Buttons and the main action, as #RRGGBB.")
    aic_color_highlight = fields.Char(string="Highlight colour", help="\"You are here\" marks, as #RRGGBB.")
    aic_color_ink = fields.Char(string="Ink colour", help="Headings, totals and the action bar, as #RRGGBB.")
    aic_logo_colors = fields.Char(
        string="Colours found in the logo", compute="_compute_aic_logo_colors", store=True,
        help="JSON list of [hex, share] pairs, most used first.")
    aic_app_icons = fields.Selection(
        [("line", "Line icons"), ("odoo", "Odoo's icons")], string="App icons",
        default="line", required=True,
        help="Line icons: each known app gets one line icon in the action colour, on a light tile.\n"
             "Odoo's icons: the colourful icons apps ship with. Icons chosen in Studio are always kept.")
    aic_palette_light = fields.Text(compute="_compute_aic_palette", store=True)
    aic_palette_dark = fields.Text(compute="_compute_aic_palette", store=True)

    # ------------------------------------------------------------------ logo colours
    def _aic_logo_bytes(self):
        self.ensure_one()
        value = self.logo
        if not value:
            return None
        if isinstance(value, (bytes, str)):    # Odoo 19 binary fields hold base64
            try:
                data = base64.b64decode(value)
            except Exception:
                return None
        else:
            return None
        # the placeholder Odoo gives a company without a logo has no brand colours to take
        if data and data == base64.b64decode(self._get_logo()):
            return None
        return data

    @api.depends("partner_id.image_1920")
    def _compute_aic_logo_colors(self):
        for company in self:
            colors = []
            data = company._aic_logo_bytes()
            if data:
                try:
                    if palette.is_svg(data):
                        # Pillow cannot read SVG: the shapes' fills, else a bitmap the SVG wraps
                        colors = palette.extract_svg_colors(data)
                        for embedded in ([] if colors else palette.svg_embedded_images(data)):
                            image = ImageProcess(base64.b64decode(embedded)).image
                            colors = palette.extract_logo_colors(image) if image else []
                            if colors:
                                break
                    else:
                        image = ImageProcess(data).image
                        if image:
                            colors = palette.extract_logo_colors(image)
                except Exception:   # not an image, or an image Pillow cannot read
                    _logger.info("aic_theme: could not read the logo of company %s", company.id, exc_info=True)
            company.aic_logo_colors = json.dumps([[c, round(s, 3)] for c, s in colors])

    # ------------------------------------------------------------------ palette
    def _aic_skin_profile(self):
        """What the palette engine needs to know about the look in use, as derive_roles() keywords:
        ``ground`` (the effective pane colour links and muted text are tuned against) and
        ``house_highlight``. Looks override this for their own skin value."""
        return {}

    def _aic_preset_roles(self, preset):
        """Role colours of a ready-made palette (``{"light": {...}, "dark": {...}, "custom": True}``), or
        None. Looks that add presets to aic_palette_preset override this."""
        return None

    def _aic_palette_css(self, roles, scheme):
        """The <style> body for these roles. Looks whose stylesheet needs other properties override it."""
        return palette.palette_css(roles, scheme)

    def _aic_roles(self):
        self.ensure_one()
        profile = self._aic_skin_profile()
        if self.aic_palette_mode == "preset":
            return self._aic_preset_roles(self.aic_palette_preset) or palette.derive_roles(**profile)
        if self.aic_palette_mode == "logo":
            try:
                colors = [tuple(c) for c in json.loads(self.aic_logo_colors or "[]")]
            except ValueError:
                colors = []
            return palette.derive_roles(colors=colors, keep_house_highlight=self.aic_keep_house_highlight, **profile)
        if self.aic_palette_mode == "custom":
            return palette.derive_roles(
                action=self.aic_color_action, highlight=self.aic_color_highlight,
                ink=self.aic_color_ink, keep_house_highlight=self.aic_keep_house_highlight, **profile)
        return self._aic_house_roles()

    def _aic_house_roles(self):
        """The look's own colours as roles (for the settings preview and documents); a house palette
        adds nothing to the page, its colours are the look's stylesheet."""
        return palette.derive_roles(**self._aic_skin_profile())

    @api.depends("aic_palette_mode", "aic_palette_preset", "aic_keep_house_highlight", "aic_color_action",
                 "aic_color_highlight", "aic_color_ink", "aic_logo_colors", "aic_skin")
    def _compute_aic_palette(self):
        for company in self:
            roles = company._aic_roles()
            company.aic_palette_light = company._aic_palette_css(roles, "light")
            company.aic_palette_dark = company._aic_palette_css(roles, "dark")

    @api.constrains("aic_color_action", "aic_color_highlight", "aic_color_ink")
    def _check_aic_colors(self):
        for company in self:
            for name in ("aic_color_action", "aic_color_highlight", "aic_color_ink"):
                value = company[name]
                if value and not palette.is_hex(value):
                    raise ValidationError(
                        self.env._("“%(value)s” is not a colour. Use the #RRGGBB form, for example #FF6A2B.", value=value))

    def aic_apply_document_colors(self):
        """Give printed documents and e-mails the company's House colours: the ink for document titles and the
        action colour in its readable text form (the link role, AA on white) for their accents and small labels
        (Odoo's Document Layout), and the action colour with its readable text for e-mail buttons (when mail is
        installed). Odoo's own fields, so its layouts keep working."""
        for company in self:
            light = company._aic_roles()["light"]
            values = {"primary_color": light["head"], "secondary_color": light["link"]}
            if "email_secondary_color" in company._fields:
                values.update(email_secondary_color=light["act"], email_primary_color=light["act_ink"])
            company.write(values)
        return True

    def aic_login_theme(self):
        """For the sign-in pages (web.login_layout): whether the Core look is on, and the company's
        light palette <style> body ('' for the house palette). Read with sudo by the template."""
        self.ensure_one()
        enabled = self.env["res.config.settings"]._aic_theme_enabled()
        return {"enabled": enabled, "skin": self._aic_effective_skin() or "" if enabled else "",
                "css": self.aic_palette_for("light") if enabled else ""}

    def _aic_effective_skin(self):
        """The skin to render for this company: its own choice when that skin is installed, else the
        last skin installed (aic_theme.default_skin), else any installed skin; False when none is."""
        values = [value for value, _label in (self._fields["aic_skin"].selection or [])]
        company = self[:1] or self.env.company
        if company.aic_skin in values:
            return company.aic_skin
        default = self.env["ir.config_parameter"].sudo().get_param(SKIN_PARAM)
        if default in values:
            return default
        return values[0] if values else False

    def _aic_window_color(self, scheme="light"):
        """The colour of the window behind the backend (the installed app's status bar and start-up
        screen): the look's ground for the scheme. Looks with another ground override this."""
        self.ensure_one()
        if scheme == "dark":
            return self._aic_roles()["dark"]["surface"]
        return "#FFFFFF"

    def aic_palette_for(self, scheme):
        """The <style> body for this company and colour scheme ('' for the house palette)."""
        self.ensure_one()
        return (self.aic_palette_dark if scheme == "dark" else self.aic_palette_light) or ""

    def aic_preview_roles(self):
        """Role colours and their contrast ratios, for the settings preview."""
        self.ensure_one()
        roles = self._aic_roles()
        light, dark = roles["light"], roles["dark"]
        c = palette.contrast
        return [
            ("Action", light["act"], light["act_ink"], c(light["act"], light["act_ink"]), dark["act"], dark["act_ink"], c(dark["act"], dark["act_ink"])),
            ("Highlight", light["hi"], light["hi_ink"], c(light["hi"], light["hi_ink"]), dark["hi"], dark["hi_ink"], c(dark["hi"], dark["hi_ink"])),
            ("Ink", palette.WHITE, light["head"], c(light["head"], palette.WHITE), dark["surface_high"], dark["head"], c(dark["head"], dark["surface_high"])),
            ("Link", palette.WHITE, light["link"], c(light["link"], palette.WHITE), dark["surface_high"], dark["link"], c(dark["link"], dark["surface_high"])),
            ("Muted text", palette.WHITE, light["muted"], c(light["muted"], palette.WHITE), dark["surface_high"], dark["muted"], c(dark["muted"], dark["surface_high"])),
        ]
