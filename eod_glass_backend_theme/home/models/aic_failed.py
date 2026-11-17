# -*- coding: utf-8 -*-
"""Home: "Failed to send", the current user's own sends that did not go out.

Odoo marks a failed e-mail or text message with a red envelope on the message in the chatter, and lists
failures in the messaging menu; WhatsApp failures appear on the WhatsApp message only. Nothing tells the
person who sent the quotation that it never arrived. This panel gathers them on Home for every role:
e-mails and text messages (mail.notification in "bounce" / "exception") and, when the WhatsApp app is
installed, WhatsApp messages ("error" / "bounced"), sent by the current user in the last 30 days, one row
per document, newest first.

Retry puts the failed e-mails back in the outgoing queue (mail.mail.action_retry: the address is read again
when it goes, so a corrected contact is used) and resends failed WhatsApp messages. Dismiss is Odoo's own
"dismiss" of the messaging menu for e-mail and text messages; WhatsApp messages are not changed, Home only
stops showing those failed until then. Both act on the current user's own sends only.
"""
from datetime import timedelta

from odoo import api, fields, models
from odoo.exceptions import AccessError

FAILED_DAYS = 30
FAILED_SCAN = 500     # newest failed sends looked at (a panel shows a handful; the badge counts documents)
FAILED_LIMIT = 5


class AicHomeFailed(models.AbstractModel):
    _inherit = "aic.home"

    # ------------------------------------------------------------------ data
    def _aic_failed_since(self):
        since = fields.Datetime.now() - timedelta(days=FAILED_DAYS)
        seen = self.env.user.sudo().aic_home_failed_seen
        return since, (seen if seen and seen > since else since)

    def _aic_failed_notifications(self, since):
        return self.env["mail.notification"].sudo().search([
            ("author_id", "=", self.env.user.partner_id.id),
            ("notification_status", "in", ("bounce", "exception")),
            ("mail_message_id.date", ">=", since),
        ], order="id desc", limit=FAILED_SCAN)

    def _aic_failed_whatsapp(self, since):
        if not self._has("whatsapp.message"):
            return None
        return self.env["whatsapp.message"].sudo().search([
            ("create_uid", "=", self.env.uid), ("state", "in", ("error", "bounced")), ("create_date", ">=", since),
        ], order="id desc", limit=FAILED_SCAN)

    def _aic_failed_rows(self):
        """{(model, res_id): {"when", "channels", "who", "why", "n"}} for documents the user can read."""
        since, wa_since = self._aic_failed_since()
        sends = []    # (model, res_id, when, channel, who, why)
        Notif = self.env["mail.notification"]
        reasons = dict(Notif._fields["failure_type"]._description_selection(self.env))
        channels = dict(Notif._fields["notification_type"]._description_selection(self.env))
        for notif in self._aic_failed_notifications(since):
            message = notif.mail_message_id
            sends.append((message.model, message.res_id, message.date, channels.get(notif.notification_type, ""),
                          notif.res_partner_id.display_name or notif.mail_email_address or "",
                          reasons.get(notif.failure_type) or (notif.failure_reason or "").split("\n")[0][:80]))
        whatsapp = self._aic_failed_whatsapp(wa_since)
        if whatsapp:
            wa_reasons = dict(whatsapp._fields["failure_type"]._description_selection(self.env))
            for wa in whatsapp:
                message = wa.mail_message_id
                sends.append((message.model, message.res_id, wa.create_date, "WhatsApp", wa.mobile_number or "",
                              wa_reasons.get(wa.failure_type) or self.env._("Failed")))
        # what the user may read, one check per model (a busy sender has hundreds of failures)
        by_model = {}
        for model, res_id, *_rest in sends:
            if model and res_id and model in self.env:
                by_model.setdefault(model, set()).add(res_id)
        readable = set()
        for model, ids in by_model.items():
            records = self.env[model].browse(list(ids)).exists()._filtered_access("read")
            readable.update((model, rid) for rid in records.ids)
        rows = {}
        for model, res_id, when, channel, who, why in sends:
            if (model, res_id) not in readable:
                continue
            row = rows.setdefault((model, res_id), {"when": when, "channels": [], "who": [], "why": [], "n": 0})
            row["n"] += 1
            row["when"] = max(row["when"], when)
            for key, value in (("channels", channel), ("who", who), ("why", why)):
                if value and value not in row[key]:
                    row[key].append(value)
        return rows

    def _aic_failed_company(self):
        """For administrators: the failed sends of everyone (documents with a failed e-mail or text message, and
        failed WhatsApp messages), last 30 days, with the list to open. None for everyone else."""
        if not self.env.user.has_group("base.group_system"):
            return None
        since = fields.Datetime.now() - timedelta(days=FAILED_DAYS)
        domain = [("has_error", "=", True), ("date", ">=", fields.Datetime.to_string(since))]
        n = self.env["mail.message"].search_count(domain)
        if self._has("whatsapp.message"):
            n += self.env["whatsapp.message"].search_count([("state", "in", ("error", "bounced")), ("create_date", ">=", since)])
        if not n:
            return None
        return {"label": self.env._("Everyone's failed sends (%(n)s)", n=n),
                "action": dict(self._action(self.env._("Failed sends"), "mail.message", domain),
                               views=[[False, "list"], [False, "form"]])}

    def _aic_failed_sends(self, data, ctx):
        rows = self._aic_failed_rows()
        data["failed_count"] = len(rows)
        company = self._aic_failed_company()
        if not rows and company:
            # nothing of the administrator's own: the panel still offers the company-wide list
            data["panels"].insert(0, self._panel("failed", self.env._("Failed to send"), [], "", "plain",
                                                 self.env._("None of yours. Across the company, last %(days)s days:", days=FAILED_DAYS),
                                                 footer=company))
            return
        if not rows:
            return
        now = fields.Datetime.now()
        items = []
        for (model, res_id), row in sorted(rows.items(), key=lambda kv: kv[1]["when"], reverse=True)[:FAILED_LIMIT]:
            record = self.env[model].browse(res_id)
            who = ", ".join(row["who"][:2]) + ("…" if len(row["who"]) > 2 else "")
            sub = self.env._("%(channel)s to %(who)s", channel=" · ".join(row["channels"]), who=who) if who else " · ".join(row["channels"])
            items.append({
                "title": record.display_name, "sub": " · ".join(filter(None, [sub, ", ".join(row["why"][:2])])),
                "right": "", "note": self._aic_failed_age(row["when"], now), "tone": "late",
                "chip": self.env._("%(n)s sends", n=row["n"]) if row["n"] > 1 else "", "chip_tone": "late",
                "model": model, "res_id": res_id,
            })
        actions = [{"label": self.env._("Retry"), "method": "retry_failed_sends", "primary": True},
                   {"label": self.env._("Dismiss"), "method": "dismiss_failed_sends"}]
        panel = self._panel("failed", self.env._("Failed to send"), items, len(rows), "late",
                            self.env._("Your own sends, last %(days)s days", days=FAILED_DAYS))
        panel["actions"] = actions
        if company:
            panel["footer"] = company
        data["panels"].insert(0, panel)

    def _aic_failed_age(self, when, now):
        seconds = max(0, (now - when).total_seconds())
        if seconds < 3600:
            return self.env._("%(n)s min ago", n=max(1, int(seconds // 60)))
        if seconds < 86400:
            return self.env._("%(n)sh ago", n=int(seconds // 3600))
        return self.env._("%(n)sd ago", n=int(seconds // 86400))

    # ------------------------------------------------------------------ actions (current user's own sends)
    @api.model
    def retry_failed_sends(self):
        """Queue the user's failed e-mails again and resend their failed WhatsApp messages. Returns a sentence."""
        since, wa_since = self._aic_failed_since()
        notifications = self._aic_failed_notifications(since).filtered(
            lambda n: n.notification_type == "email" and n.notification_status == "exception"
            and n.mail_mail_id.state == "exception")
        mails = notifications.mail_mail_id
        mails.action_retry()
        # queued again: Odoo's own "ready" status (the mail's result sets it to sent or back to exception),
        # so the panel and the chatter's red envelope do not show a send that is on its way
        notifications.write({"notification_status": "ready", "failure_type": False, "failure_reason": False})
        notifications.mail_message_id._notify_message_notification_update()
        whatsapp = self._aic_failed_whatsapp(wa_since)
        whatsapp = whatsapp.filtered(lambda w: w.state == "error") if whatsapp is not None else []
        if whatsapp:
            whatsapp.button_resend()
        n = len(mails) + len(whatsapp)
        if not n:
            return self.env._("Nothing to retry: these failed for a reason a retry cannot fix (a bounce or a "
                              "missing address). Open the document and correct the contact.")
        return self.env._("%(n)s sends queued again.", n=n)

    @api.model
    def dismiss_failed_sends(self):
        """Odoo's own dismiss for e-mail and text messages; WhatsApp failures stop showing on Home."""
        # Odoo's dismiss works per document model (it is what the messaging menu calls for each failure group)
        since, _wa = self._aic_failed_since()
        for notif_type, model in {(n.notification_type, n.mail_message_id.model)
                                  for n in self._aic_failed_notifications(since)}:
            if model in self.env and hasattr(self.env[model], "notify_cancel_by_type"):
                try:
                    self.env[model].notify_cancel_by_type(notif_type)
                except AccessError:
                    continue
        self.env.user.sudo().aic_home_failed_seen = fields.Datetime.now()
        return self.env._("Dismissed.")
