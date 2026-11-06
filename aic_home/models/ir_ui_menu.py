# -*- coding: utf-8 -*-
from odoo import api, models


class IrUiMenu(models.Model):
    _inherit = "ir.ui.menu"

    @api.model
    def _visible_menu_ids(self, debug=False):
        """Home is sold with a look: without one its web client is not loaded (aic_theme ir_asset.py), so its menu
        is hidden too."""
        ids = super()._visible_menu_ids(debug)
        if not self.env["res.company"]._aic_look_installed():
            home = self.env["ir.model.data"]._xmlid_to_res_id("aic_home.menu_aic_home_root", raise_if_not_found=False)
            if home in ids:
                ids = frozenset(ids) - {home}
        return ids
