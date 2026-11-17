# -*- coding: utf-8 -*-
from odoo import fields, models

START_PARAM = "aic_home.start_screen"


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    aic_home_start_screen = fields.Boolean(
        string="Open Home after login", config_parameter=START_PARAM, default=True,
        help="Users without their own home action land on Home instead of the app menu.")
