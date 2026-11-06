# -*- coding: utf-8 -*-
from odoo import api, fields, models
from odoo.tools.mail import html_to_inner_content

# Records whose form opens on the customer's last message (the widget is put in by the web client)
AIC_LAST_MESSAGE_MODELS = ("helpdesk.ticket",)


class MailMessage(models.Model):
    _inherit = "mail.message"

    @api.model
    def aic_last_customer_message(self, model, res_id):
        """The customer's last public message on a record (e-mail or "Send message"), for the card at the top of a
        ticket: who wrote it, when, an excerpt, and whether the team has answered since. False when there is none
        or the user may not read the record."""
        if model not in AIC_LAST_MESSAGE_MODELS or model not in self.env:
            return False
        record = self.env[model].browse(int(res_id)).exists()
        if not record or not record.has_access("read"):
            return False
        partner = record.partner_id.commercial_partner_id if "partner_id" in record._fields else self.env["res.partner"]
        if not partner:
            return False
        comment = self.env.ref("mail.mt_comment")
        base = [("model", "=", model), ("res_id", "=", record.id), ("message_type", "in", ("email", "comment")),
                ("subtype_id", "=", comment.id)]
        Message = self.sudo()   # the record is readable: its public messages are too
        # the customer's people, never staff (a customer can be a contact of the company itself)
        customer = [("author_id", "child_of", partner.id), "|", ("author_id.user_ids", "=", False), ("author_id.user_ids.share", "=", True)]
        last = Message.search(base + customer, order="date desc, id desc", limit=1)
        if not last:
            return False
        answered = bool(Message.search_count(base + [("date", ">=", last.date), ("id", "!=", last.id),
                                                     ("author_id.user_ids.share", "=", False)], limit=1))
        text = " ".join((html_to_inner_content(last.body or "") or last.subject or "").split())
        return {
            "id": last.id,
            "author": last.author_id.display_name or last.email_from or "",
            "date": fields.Datetime.to_string(last.date),
            "text": text[:400] + ("…" if len(text) > 400 else ""),
            "via_email": last.message_type == "email",
            "answered": answered,
        }
