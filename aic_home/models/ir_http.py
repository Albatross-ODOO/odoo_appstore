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
        user = self.env.user
        if (info.get("uid") and not info.get("home_action_id") and user._is_internal()
                and str(self.env["ir.config_parameter"].sudo().get_param(START_PARAM, "True")).lower() not in ("false", "0", "")):
            action = self.env.ref("aic_home.action_aic_home", raise_if_not_found=False)
            if action:
                info["home_action_id"] = action.id
        return info
