# -*- coding: utf-8 -*-
from odoo import fields, models

SHARE_PARAM = "aic_send.whatsapp_share"


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    aic_whatsapp_share = fields.Boolean(
        string="WhatsApp button in the chatter", config_parameter=SHARE_PARAM, default=True,
        help="Share any record on WhatsApp with a ready message and, for documents with a customer portal, "
             "a secure link.")
