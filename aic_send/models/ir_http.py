# -*- coding: utf-8 -*-
from odoo import models

from .res_config_settings import SHARE_PARAM


class IrHttp(models.AbstractModel):
    _inherit = "ir.http"

    def session_info(self):
        info = super().session_info()
        if info.get("uid") and self.env.user._is_internal():
            info["aic_whatsapp_share"] = str(self.env["ir.config_parameter"].sudo().get_param(SHARE_PARAM, "True")).lower() not in ("false", "0", "")
        return info
