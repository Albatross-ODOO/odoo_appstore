# -*- coding: utf-8 -*-
"""Swipe actions on phone cards (design M2): swipe a kanban card left to reveal a few keys.

Generic keys work on any model: Call (the record's or its contact's number), WhatsApp (the theme's share
sheet when installed, else a wa.me link) and Plan (schedule an activity, for models with activities).
One main key per record comes from ``_aic_swipe_primary``: the next step of common documents. Other
modules extend that method to add their own (return ``(label, method_name)`` or ``None``).
"""
import re

from odoo import api, models
from odoo.exceptions import AccessError


class AicSwipe(models.AbstractModel):
    _name = "aic.swipe"
    _description = "Core phone swipe actions"

    @api.model
    def get_actions(self, res_model, res_id):
        if not res_model or res_model not in self.env or not res_id:
            return {}
        record = self.env[res_model].browse(res_id).exists()
        if not record:
            return {}
        try:
            record.check_access("read")
        except AccessError:
            return {}
        phone = self._aic_swipe_phone(record)
        digits = re.sub(r"\D", "", phone)
        actions = {
            "tel": "tel:" + re.sub(r"[^\d+]", "", phone) if phone else "",
            "whatsapp": "",
            "whatsapp_url": "",
            "plan": "activity_ids" in record._fields,
            "primary": False,
        }
        if "aic.whatsapp.share" in self.env and str(self.env["ir.config_parameter"].sudo().get_param(
                "aic_send.whatsapp_share", "True")).lower() not in ("false", "0", ""):
            actions["whatsapp"] = "aic_send.action_whatsapp_share"
        elif len(digits) >= 8:
            actions["whatsapp_url"] = "https://wa.me/" + digits
        primary = self._aic_swipe_primary(record)
        if primary:
            try:
                record.check_access("write")
                actions["primary"] = {"label": primary[0], "method": primary[1]}
            except AccessError:
                pass
        return actions

    @api.model
    def _aic_swipe_phone(self, record):
        if "phone" in record._fields and record.phone:
            return record.phone
        if record._name != "res.partner" and "partner_id" in record._fields and record.partner_id:
            return record.partner_id.phone or ""
        return ""

    @api.model
    def _aic_swipe_primary(self, record):
        """The record's next step as (label, button method), or None. Only steps a user would press on
        the record's own form, and only in the state where that button shows."""
        model = record._name
        if model == "sale.order" and record.state in ("draft", "sent"):
            return self.env._("Confirm"), "action_confirm"
        if model == "purchase.order" and record.state in ("draft", "sent"):
            return self.env._("Confirm"), "button_confirm"
        if model == "crm.lead" and record.type == "opportunity" and record.active \
                and record._fields.get("won_status") and record.won_status == "pending":
            return self.env._("Won"), "action_set_won_rainbowman"
        if model == "account.move" and record.state == "draft" and record.is_invoice():
            return self.env._("Confirm"), "action_post"
        return None
