# -*- coding: utf-8 -*-
"""The installed app (PWA) in the company's brand: its name, icons and colours.

Odoo's web manifest names the app "Odoo", draws Odoo's icon and colours the window purple. With the
Core theme on, the manifest takes the company's name and logo instead (controllers/webmanifest.py).
A company without a logo keeps Odoo's icons.
"""
import hashlib
import io

from PIL import Image

from odoo import models

# share of the icon's side the logo may fill: "any" icons show the whole square, a maskable icon
# is cut to a circle or squircle by the launcher, so its logo stays inside the 80 % safe zone
LOGO_SHARE = {"any": 0.72, "maskable": 0.56}
ICON_SIZES = (180, 192, 512)


class ResCompany(models.Model):
    _inherit = "res.company"

    def _aic_app_name(self):
        """The installed app's name: Odoo's own setting when an admin changed it, else the company name."""
        self.ensure_one()
        name = self.env["ir.config_parameter"].sudo().get_param("web.web_app_name")
        if name and name != "Odoo":
            return name
        return self.name or "Odoo"

    def _aic_app_logo(self):
        """The company logo as bytes, or None when it is Odoo's placeholder (no brand to show)."""
        self.ensure_one()
        return self._aic_logo_bytes()

    def _aic_app_icon_version(self):
        """Changes whenever the logo changes, so browsers and launchers fetch the new icon."""
        self.ensure_one()
        data = self._aic_app_logo()
        return hashlib.sha1(data).hexdigest()[:10] if data else ""

    def _aic_app_icon(self, size, purpose="any"):
        """A square PNG of ``size`` px: the logo centred on white. None without a logo."""
        self.ensure_one()
        data = self._aic_app_logo()
        if not data or size not in ICON_SIZES or purpose not in LOGO_SHARE:
            return None
        try:
            logo = Image.open(io.BytesIO(data))
            logo.load()
        except Exception:   # not an image Pillow can read: keep Odoo's icon
            return None
        logo = logo.convert("RGBA")
        bbox = logo.getbbox()        # drop transparent margins so the mark fills its box
        if bbox:
            logo = logo.crop(bbox)
        box = max(1, round(size * LOGO_SHARE[purpose]))
        logo.thumbnail((box, box), Image.LANCZOS)
        if logo.width < box and logo.height < box:   # a small logo is enlarged to fill its box
            ratio = box / max(logo.width, logo.height)
            logo = logo.resize((max(1, round(logo.width * ratio)), max(1, round(logo.height * ratio))), Image.LANCZOS)
        canvas = Image.new("RGBA", (size, size), (255, 255, 255, 255))
        canvas.alpha_composite(logo, ((size - logo.width) // 2, (size - logo.height) // 2))
        out = io.BytesIO()
        canvas.convert("RGB").save(out, format="PNG", optimize=True)
        return out.getvalue()

    def _aic_app_theme_color(self, scheme="light"):
        """The window / status bar colour: the look's ground for the scheme."""
        self.ensure_one()
        return self._aic_window_color(scheme)
