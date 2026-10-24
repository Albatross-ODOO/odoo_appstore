# -*- coding: utf-8 -*-
from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    aic_glass_tint = fields.Boolean(related="company_id.aic_glass_tint", readonly=False)
