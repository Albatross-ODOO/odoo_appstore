# -*- coding: utf-8 -*-
"""Home: "For you", the messages that wait for the person — unread mentions and inbox notifications (Odoo's
own inbox: the needaction messages) and conversations with unread messages (direct and group chats). Home is the
one place for what needs you: activities in Missed / Today, approvals in To approve, messages here."""
from odoo import api, models
from odoo.tools.mail import html_to_inner_content

FOR_YOU_LIMIT = 5


class AicHomeForYou(models.AbstractModel):
    _inherit = "aic.home"

    def _aic_for_you(self, data, ctx):
        Message = self.env["mail.message"]
        inbox = Message.search([("needaction", "=", True)], order="id desc", limit=FOR_YOU_LIMIT)
        n_inbox = Message.search_count([("needaction", "=", True)]) if inbox else 0
        chats = self.env["discuss.channel.member"].search([
            ("partner_id", "=", self.env.user.partner_id.id), ("channel_id.channel_type", "in", ("chat", "group")),
        ]).filtered(lambda m: m.message_unread_counter > 0)
        if not inbox and not chats:
            return
        items = []
        for member in chats.sorted(lambda m: m.channel_id.last_interest_dt or m.create_date, reverse=True)[:FOR_YOU_LIMIT]:
            channel = member.channel_id
            others = (channel.channel_member_ids.partner_id - self.env.user.partner_id).mapped("display_name")
            items.append({
                "title": ", ".join(others) if channel.channel_type == "chat" and others else channel.display_name, "sub": self.env._("%(n)s unread", n=member.message_unread_counter),
                "right": "", "note": "", "tone": "hot", "chip": self.env._("Chat"), "chip_tone": "plain",
                "model": "discuss.channel", "res_id": channel.id,
            })
        for message in inbox[: max(0, FOR_YOU_LIMIT - len(items))]:
            text = " ".join((html_to_inner_content(message.body or "") or message.subject or "").split())
            items.append({
                "title": message.record_name or message.author_id.display_name or self.env._("Message"),
                "sub": (message.author_id.display_name + ": " if message.author_id else "") + (text[:90] + ("…" if len(text) > 90 else "")),
                "right": "", "note": "", "tone": "hot", "chip": "", "chip_tone": "plain",
                "model": message.model or "", "res_id": message.res_id or 0,
            })
        total = n_inbox + len(chats)
        data["for_you_count"] = total
        panel = self._panel("foryou", self.env._("For you"), items, total, "hot",
                            self.env._("Mentions, your inbox and unread chats"),
                            footer={"label": self.env._("Open Discuss"), "action": {"xmlid": "mail.action_discuss"}})
        data["panels"].insert(1 if data["panels"] and data["panels"][0]["key"] == "failed" else 0, panel)
