# -*- coding: utf-8 -*-
"""Home: "My week", the second view of Home.

What the person got done this week next to last week, and what is still open: activities completed per day
(a "done" activity is the message Odoo posts when someone marks it done, authored by that person) against
activities due that day, what is overdue now, and the work moved in the installed apps (opportunities won,
orders confirmed, transfers done…). The week starts on the language's first day of the week.

A team lead (the leader of a sales team, or the manager of employees in the Employees app) also sees each
team member's load: overdue, still due this week, done this week. Alphabetical, never ranked: it is there to
see who is overloaded, not who is first. Only counts are read for colleagues, never their records.
"""
from datetime import datetime, time, timedelta

import pytz

from odoo import api, fields, models
from odoo.exceptions import AccessError
from odoo.tools.misc import format_date

TEAM_LIMIT = 25
WORK_LIMIT = 6


class AicHomeWeek(models.AbstractModel):
    _inherit = "aic.home"

    # ------------------------------------------------------------------ bounds
    def _aic_week_bounds(self, today):
        lang = self.env["res.lang"]._lang_get(self.env.lang or "en_US")
        first = int(lang.week_start) if lang and lang.week_start else 1          # 1 = Monday … 7 = Sunday
        start = today - timedelta(days=(today.isoweekday() - first) % 7)
        tz = pytz.timezone(self.env.user.tz or "UTC")

        def utc(day):
            return tz.localize(datetime.combine(day, time.min)).astimezone(pytz.utc).replace(tzinfo=None)

        return {"start": start, "end": start + timedelta(days=7), "prev": start - timedelta(days=7),
                "start_dt": utc(start), "end_dt": utc(start + timedelta(days=7)), "prev_dt": utc(start - timedelta(days=7)),
                "today": today, "tz": tz}

    def _aic_local_day(self, dt, tz):
        return pytz.utc.localize(dt).astimezone(tz).date()

    # ------------------------------------------------------------------ activities
    def _aic_done_dates(self, partner_ids, start_dt, end_dt):
        """{partner_id: [local dates]} of activities marked done in [start, end). Counts only."""
        messages = self.env["mail.message"].sudo().search_fetch([
            ("author_id", "in", partner_ids), ("mail_activity_type_id", "!=", False),
            ("date", ">=", start_dt), ("date", "<", end_dt),
        ], ["author_id", "date"], limit=20000)
        out = {}
        for message in messages:
            out.setdefault(message.author_id.id, []).append(message.date)
        return out

    @api.model
    def get_week_data(self):
        user = self.env.user
        role = user._aic_effective_role()
        today = fields.Date.context_today(self)
        b = self._aic_week_bounds(today)
        partner = user.partner_id.id

        done = self._aic_done_dates([partner], b["prev_dt"], b["end_dt"]).get(partner, [])
        done_days = [self._aic_local_day(d, b["tz"]) for d in done]
        done_week = [d for d in done_days if d >= b["start"]]
        Activity = self.env["mail.activity"]
        due_rows = Activity._read_group(
            [("user_id", "=", user.id), ("date_deadline", ">=", b["start"]), ("date_deadline", "<", b["end"])],
            ["date_deadline:day"], ["__count"])
        due_by_day = {day.date() if hasattr(day, "date") else day: n for day, n in due_rows}
        days = []
        for i in range(7):
            day = b["start"] + timedelta(days=i)
            days.append({
                "label": format_date(self.env, day, date_format="EEE"),
                "date": format_date(self.env, day, date_format="d MMM"),
                "done": sum(1 for d in done_week if d == day),
                "due": due_by_day.get(day, 0),
                "is_today": day == today, "is_past": day < today,
            })
        overdue_domain = [("user_id", "=", user.id), ("date_deadline", "<", today)]
        still_due_domain = [("user_id", "=", user.id), ("date_deadline", ">=", today), ("date_deadline", "<", b["end"])]
        data = {
            "label": self.env._("%(start)s – %(end)s", start=format_date(self.env, b["start"], date_format="d MMM"),
                                end=format_date(self.env, b["end"] - timedelta(days=1), date_format="d MMM")),
            "days": days,
            "done": len(done_week),
            "done_prev": len(done_days) - len(done_week),
            "still_due": Activity.search_count(still_due_domain),
            "overdue": Activity.search_count(overdue_domain),
            "still_due_action": self._action(self.env._("Still due this week"), "mail.activity", still_due_domain),
            "overdue_action": self._action(self.env._("Overdue activities"), "mail.activity", overdue_domain),
            "work": self._aic_week_work(role, b),
            "team": self._aic_week_team(b),
        }
        data["summary"] = self._aic_week_summary(data)
        return data

    def _aic_week_summary(self, data):
        # one sentence per count, singular for one (Odoo's Python translations have no plural forms)
        if data["done"] == 1:
            parts = [self.env._("You completed 1 activity this week (%(prev)s last week).", prev=data["done_prev"])]
        else:
            parts = [self.env._("You completed %(n)s activities this week (%(prev)s last week).", n=data["done"], prev=data["done_prev"])]
        if data["still_due"] == 1:
            parts.append(self.env._("1 is still due before the week ends."))
        elif data["still_due"]:
            parts.append(self.env._("%(n)s are still due before the week ends.", n=data["still_due"]))
        if data["overdue"] == 1:
            parts.append(self.env._("1 is overdue."))
        elif data["overdue"]:
            parts.append(self.env._("%(n)s are overdue.", n=data["overdue"]))
        return " ".join(parts)

    # ------------------------------------------------------------------ work moved
    def _aic_week_work(self, role, b):
        uid = self.env.uid
        d0, d1, p0 = b["start"], b["end"], b["prev"]
        t0, t1, tp = b["start_dt"], b["end_dt"], b["prev_dt"]
        labels = {
            "won": self.env._("Opportunities won"),
            "new_leads": self.env._("New opportunities"),
            "quotes": self.env._("Quotations created"),
            "orders": self.env._("Orders confirmed"),
            "transfers": self.env._("Transfers done"),
            "purchases": self.env._("Purchase orders confirmed"),
            "invoices": self.env._("Invoices posted"),
            "tasks": self.env._("Tasks closed"),
            "tickets": self.env._("Tickets closed"),
        }
        # key: (model, date field, base domain, the field is a datetime)
        specs = {
            "won": ("crm.lead", "date_closed", [("user_id", "=", uid), ("stage_id.is_won", "=", True)], True),
            "new_leads": ("crm.lead", "create_date", [("user_id", "=", uid)], True),
            "quotes": ("sale.order", "create_date", [("user_id", "=", uid)], True),
            "orders": ("sale.order", "date_order", [("user_id", "=", uid), ("state", "=", "sale")], True),
            "transfers": ("stock.picking", "date_done", [("user_id", "=", uid), ("state", "=", "done")], True),
            "purchases": ("purchase.order", "date_approve", [("user_id", "=", uid), ("state", "in", ("purchase", "done"))], True),
            "invoices": ("account.move", "invoice_date",
                         [("invoice_user_id", "=", uid), ("state", "=", "posted"), ("move_type", "=", "out_invoice")], False),
            "tasks": ("project.task", "date_last_stage_update", [("user_ids", "in", uid), ("is_closed", "=", True)], True),
            "tickets": ("helpdesk.ticket", "close_date", [("user_id", "=", uid)], True),
        }
        order = {
            "sales": ["won", "orders", "quotes", "new_leads", "invoices", "tasks"],
            "warehouse": ["transfers", "purchases", "orders", "tasks"],
            "purchase": ["purchases", "transfers", "invoices"],
            "accounts": ["invoices", "orders", "purchases"],
            "service": ["tasks", "tickets", "transfers"],
            "owner": ["orders", "won", "invoices", "purchases", "transfers", "tasks", "tickets"],
        }.get(role, [])
        keys = order + [k for k in specs if k not in order]
        out = []
        for key in keys:
            model, field, base, is_dt = specs[key]
            label = labels[key]
            if model not in self.env or field not in self.env[model]._fields:
                continue
            start, end, prev = (t0, t1, tp) if is_dt else (d0, d1, p0)
            this_dom = base + [(field, ">=", start), (field, "<", end)]
            try:
                value = self.env[model].search_count(this_dom)
                previous = self.env[model].search_count(base + [(field, ">=", prev), (field, "<", start)])
            except AccessError:   # a model the user may not read: no tile
                continue
            if not value and not previous and key not in order[:2]:
                continue
            out.append({"key": key, "label": label, "value": value, "prev": previous,
                        "tone": "ok" if value > previous else "plain",
                        "action": self._action(label, model, this_dom)})
            if len(out) >= WORK_LIMIT:
                break
        return out

    # ------------------------------------------------------------------ team
    def _aic_week_team_users(self):
        users = self.env["res.users"]
        if "crm.team" in self.env:
            users |= self.env["crm.team"].sudo().search([("user_id", "=", self.env.uid)]).member_ids
        if "hr.employee" in self.env:
            Employee = self.env["hr.employee"].sudo()
            mine = Employee.search([("user_id", "=", self.env.uid)])
            if mine:
                users |= Employee.search([("parent_id", "in", mine.ids), ("user_id", "!=", False)]).user_id
        return (users - self.env.user).filtered(lambda u: u.active and not u.share)

    def _aic_week_team(self, b):
        members = self._aic_week_team_users()
        if not members:
            return None
        members = members.sorted(lambda u: (u.name or "").lower())[:TEAM_LIMIT]
        Activity = self.env["mail.activity"].sudo()
        today = b["today"]
        overdue = dict(Activity._read_group([("user_id", "in", members.ids), ("date_deadline", "<", today)], ["user_id"], ["__count"]))
        due = dict(Activity._read_group([("user_id", "in", members.ids), ("date_deadline", ">=", today),
                                         ("date_deadline", "<", b["end"])], ["user_id"], ["__count"]))
        done = self._aic_done_dates(members.partner_id.ids, b["start_dt"], b["end_dt"])
        rows = []
        for member in members:
            n_overdue = overdue.get(member, 0)
            rows.append({"id": member.id, "name": member.name, "initials": self._aic_initials(member.name),
                         "overdue": n_overdue, "due": due.get(member, 0), "done": len(done.get(member.partner_id.id, [])),
                         "tone": "late" if n_overdue >= 10 else "warn" if n_overdue else "plain"})
        return {"members": rows, "more": max(0, len(self._aic_week_team_users()) - TEAM_LIMIT)}
