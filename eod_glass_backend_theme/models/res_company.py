# -*- coding: utf-8 -*-
from odoo import api, fields, models

from . import eod_palette


class ResCompany(models.Model):
    _inherit = "res.company"

    aic_skin = fields.Selection(selection_add=[("eod", "EOD")], ondelete={"eod": "set null"})
    aic_palette_mode = fields.Selection(
        selection_add=[("house",), ("preset", "A ready-made palette")], ondelete={"preset": "set default"})
    aic_palette_preset = fields.Selection(
        selection_add=[("graphite", "Graphite & Mint"), ("iris", "Iris & Apricot")],
        ondelete={"graphite": "set null", "iris": "set null"})
    aic_glass_tint = fields.Boolean(
        string="Tint the background from these colours", default=True,
        help="EOD: the soft colour field behind the panes takes the hues of the company's colours.")

    def _aic_is_eod(self):
        self.ensure_one()
        return self._aic_effective_skin() == "eod"

    def _aic_skin_profile(self):
        if self._aic_is_eod():
            return {"ground": eod_palette.GROUND_LIGHT, "house_highlight": eod_palette.HOUSE_HIGHLIGHT}
        return super()._aic_skin_profile()

    def _aic_house_roles(self):
        if self._aic_is_eod():
            return eod_palette.LAGOON
        return super()._aic_house_roles()

    def _aic_preset_roles(self, preset):
        return eod_palette.PRESETS.get(preset) or super()._aic_preset_roles(preset)

    def _aic_palette_css(self, roles, scheme):
        if self._aic_is_eod():
            return eod_palette.glass_css(roles, scheme, tint=self.aic_glass_tint)
        return super()._aic_palette_css(roles, scheme)

    def _aic_window_color(self, scheme="light"):
        if self._aic_is_eod():
            return eod_palette.WINDOW_DARK if scheme == "dark" else eod_palette.WINDOW_LIGHT
        return super()._aic_window_color(scheme)

    @api.depends("aic_glass_tint")
    def _compute_aic_palette(self):
        return super()._compute_aic_palette()
