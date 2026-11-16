# -*- coding: utf-8 -*-
"""Core Focus queue: work through your due activities one record at a time.

Generic over every model that has activities (leads, tasks, tickets, orders…): the queue is the current
user's activities due today or earlier, oldest first. Each card brings the record's contact details, a few
facts, the latest messages and one-key actions (done, done and follow up, snooze, skip). Everything runs as
the user; a record they cannot read shows as a plain activity without details.
"""
import re
from datetime import timedelta

from odoo import api, fields, models
from odoo.exceptions import AccessError, UserError
from odoo.tools import html2plaintext
from odoo.tools.misc import format_amount, format_date

QUEUE_LIMIT = 300
NO_RECORD = "__none__"     # activities attached to no record (personal to-dos)


class AicFocus(models.AbstractModel):
    _name = "aic.focus"
    _description = "Core focus queue"

    # ------------------------------------------------------------------ queue
    def _due_domain(self, res_model=False):
        domain = [("user_id", "=", self.env.uid), ("date_deadline", "<=", fields.Date.context_today(self))]
        if res_model == NO_RECORD:
            domain.append(("res_model", "=", False))
        elif res_model:
            domain.append(("res_model", "=", res_model))
        return domain

    @api.model
    def get_counts(self):
        today = fields.Date.context_today(self)
        Activity = self.env["mail.activity"]
        due = Activity.search_count(self._due_domain())
        done = Activity.with_context(active_test=False).search_count([
            ("user_id", "=", self.env.uid), ("active", "=", False), ("date_done", "=", today)])
        return {"due": due, "done_today": done}

    @api.model
    def get_queue(self, res_model=False):
        Activity = self.env["mail.activity"]
        activities = Activity.search(self._due_domain(res_model), order="date_deadline asc, id asc", limit=QUEUE_LIMIT)
        groups = Activity._read_group(self._due_domain(), ["res_model"], ["__count"])
        names = {m.model: m.name for m in self.env["ir.model"].sudo().search([("model", "in", [g[0] for g in groups])])}
        models_ = sorted(({"model": model or NO_RECORD,
                           "label": names.get(model, model) if model else self.env._("To-dos"),
                           "count": count} for model, count in groups),
                         key=lambda m: -m["count"])
        return dict(self.get_counts(), ids=activities.ids, models=models_, res_model=res_model or False)

    # ------------------------------------------------------------------ one card
    @api.model
    def get_card(self, activity_id):
        activity = self.env["mail.activity"].browse(activity_id).exists()
        if not activity or activity.user_id.id != self.env.uid or not activity.active:
            return {"gone": True}
        today = fields.Date.context_today(self)
        late = (today - activity.date_deadline).days if activity.date_deadline else 0
        card = {
            "gone": False,
            "activity": {
                "id": activity.id,
                "title": activity.summary or activity.activity_type_id.name or self.env._("Activity"),
                "type": activity.activity_type_id.name or "",
                "icon": activity.activity_type_id.icon or "calendar_today",
                "category": activity.activity_type_id.category or "default",
                "note": self._short(html2plaintext(activity.note or ""), 600),
                "late": late,
                "when": (self.env._("Due today") if late <= 0 else self.env._("Yesterday") if late == 1
                         else self.env._("%(days)s days late", days=late)),
                "deadline": format_date(self.env, activity.date_deadline),
            },
            "record": {"model": activity.res_model, "id": activity.res_id, "name": activity.res_name or "",
                       "model_label": (self.env["ir.model"]._get(activity.res_model).name or activity.res_model)
                       if activity.res_model else self.env._("To-do")},
            "contact": {}, "facts": [], "messages": [], "other_activities": 0,
        }
        if not activity.res_model or not activity.res_id:
            return card
        try:
            record = self.env[activity.res_model].browse(activity.res_id).exists()
            if record:
                record.check_access("read")
                card["record"]["name"] = record.display_name
                card["contact"] = self._contact(record)
                card["facts"] = self._facts(record)
                card["messages"] = self._messages(record)
                card["other_activities"] = self.env["mail.activity"].search_count([
                    ("res_model", "=", activity.res_model), ("res_id", "=", activity.res_id), ("id", "!=", activity.id)])
        except (AccessError, KeyError):
            pass
        return card

    @staticmethod
    def _short(text, limit):
        text = re.sub(r"\s+", " ", text or "").strip()
        return text if len(text) <= limit else text[: limit - 1].rstrip() + "…"

    def _contact(self, record):
        fields_ = record._fields
        name = phone = email = ""
        if record._name == "res.partner":
            partner = record
        else:
            partner = record.partner_id if "partner_id" in fields_ and record.partner_id else False
        if partner:
            name, phone, email = partner.display_name, partner.phone or "", partner.email or ""
        if record._name == "crm.lead":
            name = name or record.contact_name or record.partner_name or ""
            phone = record.phone or phone
            email = record.email_from or email
        digits = re.sub(r"\D", "", phone or "")
        return {"name": name, "phone": phone or "", "email": email or "",
                "tel": "tel:" + re.sub(r"[^\d+]", "", phone) if phone else "",
                "whatsapp": "https://wa.me/" + digits if len(digits) >= 8 else ""}

    def _facts(self, record):
        facts = []
        model = record._name
        if model == "crm.lead":
            facts += [(self.env._("Expected"), format_amount(self.env, record.expected_revenue, record.company_currency)),
                      (self.env._("Probability"), "%s%%" % round(record.probability)),
                      (self.env._("Stage"), record.stage_id.name or "")]
            if record.tag_ids:
                facts.append((self.env._("Tags"), ", ".join(record.tag_ids.mapped("name"))))
        elif model == "sale.order":
            facts += [(self.env._("Total"), format_amount(self.env, record.amount_total, record.currency_id)),
                      (self.env._("Status"), dict(record._fields["state"]._description_selection(self.env)).get(record.state, ""))]
            if record.validity_date:
                facts.append((self.env._("Expires"), format_date(self.env, record.validity_date)))
        elif model == "project.task":
            facts += [(self.env._("Project"), record.project_id.name or ""), (self.env._("Stage"), record.stage_id.name or "")]
            if record.date_deadline:
                facts.append((self.env._("Deadline"), format_date(self.env, record.date_deadline)))
        elif model == "helpdesk.ticket":
            facts += [(self.env._("Team"), record.team_id.name or ""), (self.env._("Stage"), record.stage_id.name or "")]
        elif model == "account.move" and record.is_invoice():
            facts += [(self.env._("Amount due"), format_amount(self.env, record.amount_residual, record.currency_id)),
                      (self.env._("Due"), format_date(self.env, record.invoice_date_due))]
        elif model == "purchase.order":
            facts += [(self.env._("Total"), format_amount(self.env, record.amount_total, record.currency_id)),
                      (self.env._("Vendor"), record.partner_id.display_name or "")]
        return [{"label": label, "value": value} for label, value in facts if value]

    def _messages(self, record):
        messages = self.env["mail.message"].search([
            ("model", "=", record._name), ("res_id", "=", record.id),
            ("message_type", "in", ("comment", "email", "email_outgoing", "whatsapp_message")),
        ], order="id desc", limit=3)
        out = []
        for msg in messages:
            text = self._short(html2plaintext(msg.body or ""), 240)
            if not text:
                continue
            out.append({"id": msg.id, "author": msg.author_id.display_name or msg.email_from or "",
                        "date": format_date(self.env, msg.date), "text": text,
                        "note": bool(msg.subtype_id and msg.subtype_id.internal)})
        return out

    # ------------------------------------------------------------------ actions
    def _own(self, activity_id):
        activity = self.env["mail.activity"].browse(activity_id).exists()
        if not activity or activity.user_id.id != self.env.uid:
            raise UserError(self.env._("This activity is no longer in your queue."))
        # the queue holds the person's activities from every company they belong to; act in the
        # record's company, or a follow-up on another company's record is refused by its record rules
        if activity.res_model and activity.res_id and activity.res_model in self.env:
            record = self.env[activity.res_model].sudo().browse(activity.res_id).exists()
            company = record.company_id if "company_id" in record._fields else None
            if company and company in self.env.user.company_ids:
                activity = activity.with_company(company)
        return activity

    @api.model
    def mark_done(self, activity_id, feedback=False, follow_up_days=0):
        """Mark done (with the feedback logged on the record); optionally schedule the same kind of
        activity again in ``follow_up_days`` days."""
        activity = self._own(activity_id)
        values = None
        if follow_up_days:
            values = {
                "res_model_id": activity.res_model_id.id, "res_id": activity.res_id,
                "activity_type_id": activity.activity_type_id.id, "summary": activity.summary,
                "user_id": self.env.uid,
                "date_deadline": fields.Date.context_today(self) + timedelta(days=int(follow_up_days)),
            }
        activity.action_feedback(feedback=feedback or False)
        if values:
            activity.env["mail.activity"].create(values)
        return self.get_counts()

    @api.model
    def snooze(self, activity_id, days=1):
        activity = self._own(activity_id)
        activity.date_deadline = fields.Date.context_today(self) + timedelta(days=max(int(days), 1))
        return self.get_counts()

    @api.model
    def done_and_plan(self, activity_id, feedback=False):
        """Mark done and open Odoo's own dialog to plan the next activity (full control)."""
        return self._own(activity_id).action_feedback_schedule_next(feedback=feedback or False)
