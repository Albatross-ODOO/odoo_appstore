# -*- coding: utf-8 -*-
from odoo import models

from .res_config_settings import START_PARAM


class IrHttp(models.AbstractModel):
    _inherit = "ir.http"

    def session_info(self):
        """Open Home when the URL names no action and the user has no home action of their own.

        The web client already falls back to ``home_action_id`` in that case (action_plugin.js), on
        Community and Enterprise alike, so no JavaScript patch is needed. A user's own home action
        (Preferences → Home Action) always wins.
        """
        info = super().session_info()
        if info.get("uid") and not info.get("home_action_id"):
            action = self._aic_home_start_action()
            if action:
                info["home_action_id"] = action.id
        return info

    def _aic_home_start_action(self):
        """Home, for an internal user, when it is the landing page (Settings) and a look is installed (Home is
        sold with a look: see ir_ui_menu.py); otherwise nothing."""
        start = str(self.env["ir.config_parameter"].sudo().get_param(START_PARAM, "True")).lower() not in ("false", "0", "")
        if self.env.user._is_internal() and self.env["res.company"]._aic_look_installed() and start:
            return self.env.ref("aic_home.action_aic_home", raise_if_not_found=False)
        return False
