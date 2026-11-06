# -*- coding: utf-8 -*-
"""Home: everything the start screen shows, in one call.

``get_home_data`` returns plain JSON: the person, the summary sentence, Missed, Today, KPI tiles, role
panels and the preferred order of apps. Every query runs as the user (record rules and access rights
apply), and every app-specific block is built only when that app's model exists, so the module has no
dependency on sale, stock, purchase, account, project or helpdesk.

Item shape (one row in a panel):  {title, sub, right, note, tone, chip, chip_tone, model, res_id}
Panel shape:   {key, title, badge, tone, sub, items, footer: {label, action} | None, cleanup: {...} | None,
               actions?: [{label, method, primary?}] (a aic.home method the client calls, then reloads)}
KPI shape:     {key, label, value, note, tone, action}
Action shape:  {name, res_model, domain, context?}  (the client turns it into a window action)
tone / chip_tone: "hot" (butter), "ok", "warn", "late", "plain".
"""
import logging
from datetime import datetime, time, timedelta

import pytz

from odoo import api, fields, models
from odoo.exceptions import AccessError
from odoo.tools.misc import format_amount, format_date

from .res_users import ROLE_LABELS

_logger = logging.getLogger(__name__)

LIMIT = 5
SECTIONS = ("missed", "today", "apps")   # Home sections the person may hide (Customise home)

# Apps each role reaches for first (root menu xmlids); the rest follow in menu order.
ROLE_APPS = {
    "sales": ["crm.crm_menu_root", "sale.sale_menu_root", "contacts.menu_contacts", "calendar.mail_menu_calendar",
              "mail.menu_root_discuss", "account.menu_finance"],
    "warehouse": ["stock.menu_stock_root", "stock_barcode.stock_barcode_menu", "purchase.menu_purchase_root",
                  "mrp.menu_mrp_root", "contacts.menu_contacts", "mail.menu_root_discuss"],
    "purchase": ["purchase.menu_purchase_root", "stock.menu_stock_root", "account.menu_finance",
                 "contacts.menu_contacts", "mail.menu_root_discuss"],
    "accounts": ["account_accountant.menu_accounting", "account.menu_finance", "contacts.menu_contacts",
                 "sale.sale_menu_root", "purchase.menu_purchase_root", "mail.menu_root_discuss"],
    "service": ["project.menu_main_pm", "helpdesk.menu_helpdesk_root", "calendar.mail_menu_calendar",
                "contacts.menu_contacts", "mail.menu_root_discuss"],
    "owner": ["sale.sale_menu_root", "crm.crm_menu_root", "account_accountant.menu_accounting", "account.menu_finance",
              "stock.menu_stock_root", "purchase.menu_purchase_root", "mail.menu_root_discuss"],
}


class AicHome(models.AbstractModel):
    _name = "aic.home"
    _description = "Home"

    # ------------------------------------------------------------------ entry points
    @api.model
    def get_home_data(self):
        user = self.env.user
        role = user._aic_effective_role()
        today = fields.Date.context_today(self)
        ctx = {"today": today, "uid": user.id, "role": role}
        ctx.update(self._aic_day_bounds(today))

        data = {
            "user": {"name": user.name, "first": (user.name or "").split(" ")[0], "initials": self._aic_initials(user.name)},
            "company": self.env.company.name,
            "role": role,
            # the role field's own (translated) selection label: the labels are model terms, not code terms
            "role_label": dict(self.env["res.users"]._fields["aic_home_role"]._description_selection(self.env)).get(
                role, ROLE_LABELS[role]),
            "role_is_suggested": user.aic_home_role == "auto",
            # the locale's own full date ("jueves, 8 de octubre de 2026", "Donnerstag, 8. Oktober 2026")
            "date_label": format_date(self.env, today, date_format="full"),
            "greeting": self._aic_greeting(),
            "missed": [], "missed_count": 0, "team_overdue_count": 0,
            "today": [],
            "kpis": [],
            "panels": [],
            "app_order": ROLE_APPS.get(role, []),
            "app_badges": {},
        }
        data["queue"] = self.env["aic.focus"].get_counts()
        self._aic_safe(self._aic_missed, data, ctx)
        self._aic_safe(self._aic_today, data, ctx)
        builder = getattr(self, "_aic_role_%s" % role, None)
        if builder:
            self._aic_safe(builder, data, ctx)
        data["approvals_count"] = 0
        self._aic_safe(self._aic_approvals, data, ctx)        # every role: what waits for my approval
        data["for_you_count"] = 0
        self._aic_safe(self._aic_for_you, data, ctx)          # every role: mentions, inbox, unread chats
        data["failed_count"] = 0
        self._aic_safe(self._aic_failed_sends, data, ctx)     # every role: the person's own failed sends
        data["summary"] = self._aic_summary(data, role)
        self._aic_apply_layout(data, role)
        return data

    # ------------------------------------------------------------------ Customise home
    def _aic_layout(self, role):
        layout = self.env.user.sudo().aic_home_layout or {}
        entry = layout.get(role) if isinstance(layout, dict) else None
        return entry if isinstance(entry, dict) else {}

    def _aic_apply_layout(self, data, role):
        """Hide and order the blocks as the person chose for this role, and describe every block (shown or
        not) for the Customise home sheet. Blocks: "kpi:<key>" tiles, "panel:<key>" panels and the
        sections "missed", "today" and "apps". A block that is hidden today but empty (an absent panel)
        keeps its choice for the day it comes back."""
        layout = self._aic_layout(role)
        hidden = set(layout.get("hidden") or [])
        rank = {key: i for i, key in enumerate(layout.get("order") or [])}

        def arrange(blocks, prefix):
            # stable sort: chosen order first, the rest keep the role's own order after them
            blocks = sorted(blocks, key=lambda b: rank.get(prefix + b["key"], len(rank)))
            return blocks, [b for b in blocks if prefix + b["key"] not in hidden]

        all_kpis, data["kpis"] = arrange(data["kpis"], "kpi:")
        all_panels, data["panels"] = arrange(data["panels"], "panel:")
        data["sections"] = {key: key not in hidden for key in SECTIONS}
        data["layout"] = {
            "custom": bool(layout),
            "tiles": [{"key": "kpi:" + k["key"], "label": k["label"], "visible": "kpi:" + k["key"] not in hidden}
                      for k in all_kpis],
            "panels": [{"key": "panel:" + p["key"], "label": p["title"], "visible": "panel:" + p["key"] not in hidden}
                       for p in all_panels],
            "sections": [{"key": key, "label": label, "visible": key not in hidden}
                         for key, label in ((("missed", self.env._("Missed")), ("today", self.env._("Today")), ("apps", self.env._("Your apps"))))],
            # apps the person put away or reordered ("app:<menu xmlid>"): the menus and access rights are untouched,
            # Home only lists them under More apps (the client builds the rows from the menus it may open)
            "app_hidden": [key[4:] for key in hidden if key.startswith("app:")],
            "app_order": [key[4:] for key in (layout.get("order") or []) if key.startswith("app:")],
        }

    @api.model
    def save_layout(self, hidden=None, order=None):
        """Store the current user's choice for their current role, then return the new Home data."""
        def clean(keys):
            out = []
            for key in keys or []:
                if isinstance(key, str) and 0 < len(key) <= 80 and key not in out:
                    out.append(key)
            return out[:200]
        role = self.env.user._aic_effective_role()
        user = self.env.user.sudo()
        layout = dict(user.aic_home_layout or {}) if isinstance(user.aic_home_layout, dict) else {}
        layout[role] = {"hidden": clean(hidden), "order": clean(order)}
        user.aic_home_layout = layout
        return self.get_home_data()

    @api.model
    def reset_layout(self):
        """Back to the role's own layout."""
        role = self.env.user._aic_effective_role()
        user = self.env.user.sudo()
        layout = dict(user.aic_home_layout or {}) if isinstance(user.aic_home_layout, dict) else {}
        layout.pop(role, None)
        user.aic_home_layout = layout or False
        return self.get_home_data()

    @api.model
    def reschedule_missed_to_today(self):
        """Move every overdue activity of the current user to today. Returns how many moved."""
        today = fields.Date.context_today(self)
        activities = self.env["mail.activity"].search([("user_id", "=", self.env.uid), ("date_deadline", "<", today)])
        activities.write({"date_deadline": today})
        return len(activities)

    # ------------------------------------------------------------------ helpers
    def _aic_safe(self, fn, data, ctx):
        """Run one block; a block the user may not read (or a module quirk) must never break Home."""
        try:
            with self.env.cr.savepoint():
                fn(data, ctx)
        except AccessError:
            _logger.debug("aic_home: %s skipped (access)", fn.__name__)
        except Exception:
            _logger.exception("aic_home: %s failed", fn.__name__)

    def _has(self, model):
        return model in self.env

    @staticmethod
    def _aic_initials(name):
        parts = [p for p in (name or "").split() if p]
        return ("".join(p[0] for p in parts[:2]) or "?").upper()

    def _aic_greeting(self):
        tz = pytz.timezone(self.env.user.tz or "UTC")
        hour = datetime.now(tz).hour
        if hour < 12:
            return self.env._("Good morning")
        if hour < 17:
            return self.env._("Good afternoon")
        return self.env._("Good evening")

    def _aic_day_bounds(self, today):
        """Today's start / end and the next week as naive UTC datetimes, in the user's time zone."""
        tz = pytz.timezone(self.env.user.tz or "UTC")
        start = tz.localize(datetime.combine(today, time.min)).astimezone(pytz.utc).replace(tzinfo=None)
        return {"day_start": start, "day_end": start + timedelta(days=1), "week_end": start + timedelta(days=8)}

    def _fmt_time(self, dt):
        if not dt:
            return ""
        tz = pytz.timezone(self.env.user.tz or "UTC")
        return pytz.utc.localize(dt).astimezone(tz).strftime("%H:%M")

    def _money(self, amount, currency=None):
        return format_amount(self.env, amount or 0.0, currency or self.env.company.currency_id)

    def _money_short(self, amount, currency=None):
        """Compact amount for KPI tiles ("$110.5K"); the exact amount goes in the tooltip."""
        currency = currency or self.env.company.currency_id
        value = abs(amount or 0.0)
        # from 10,000 up, in thousands / millions / billions ("$17.3K"); below that, whole units
        for limit, unit, suffix in ((1e9, 1e9, "B"), (1e6, 1e6, "M"), (1e4, 1e3, "K")):
            if value >= limit:
                number = ("%.1f" % (value / unit)).rstrip("0").rstrip(".") + suffix
                break
        else:
            # under 10,000: whole units with the language's grouping ("$4,696"), never "$4,696.00" (it wraps)
            lang = self.env["res.lang"]._lang_get(self.env.lang or "en_US") or self.env["res.lang"]._lang_get("en_US")
            number = lang.format("%.0f", value, grouping=True) if lang else "%.0f" % value
        sign = "-" if (amount or 0) < 0 else ""
        symbol = currency.symbol or currency.name
        return sign + (number + "\u00a0" + symbol if currency.position == "after" else symbol + number)

    def _days_late(self, date_value, today):
        if not date_value:
            return 0
        if isinstance(date_value, datetime):
            date_value = date_value.date()
        return (today - date_value).days

    def _late_label(self, days):
        if days <= 0:
            return self.env._("Today")
        if days == 1:
            return self.env._("Yesterday")
        return self.env._("%(days)s days late", days=days)

    @staticmethod
    def _count_sum(Model, domain, field):
        """(count, total of ``field``) in one aggregate query, never reading the records themselves."""
        [(count, total)] = Model._read_group(domain, aggregates=["__count", "%s:sum" % field])
        return count, total or 0.0

    @staticmethod
    def _join(*parts):
        return " · ".join(p for p in parts if p)

    @staticmethod
    def _action(name, model, domain, context=None):
        return {"name": name, "res_model": model, "domain": domain, "context": context or {}}

    @staticmethod
    def _item(record, title, sub="", right="", note="", tone="plain", chip="", chip_tone="plain"):
        return {"title": title, "sub": sub, "right": right, "note": note, "tone": tone,
                "chip": chip, "chip_tone": chip_tone, "model": record._name, "res_id": record.id}

    @staticmethod
    def _kpi(key, label, value, note="", tone="plain", action=None, full=""):
        return {"key": key, "label": label, "value": value, "note": note, "tone": tone, "action": action,
                "full": full or value}

    @staticmethod
    def _panel(key, title, items, badge="", tone="plain", sub="", footer=None, cleanup=None):
        return {"key": key, "title": title, "items": items, "badge": str(badge) if badge != "" else "",
                "tone": tone, "sub": sub, "footer": footer, "cleanup": cleanup}

    # ------------------------------------------------------------------ Missed and Today
    def _aic_team_users(self):
        """The people who report to the current user: their direct reports in Employees and the members of the
        sales teams they lead, whichever is installed. Never the user themself."""
        uid = self.env.uid
        users = self.env["res.users"]
        if self._has("hr.employee"):
            employees = self.env["hr.employee"].sudo().search([("parent_id.user_id", "=", uid)])
            users |= employees.user_id
        if self._has("crm.team"):
            teams = self.env["crm.team"].sudo().search([("user_id", "=", uid)])
            users |= teams.member_ids
        return users.filtered(lambda u: u.id != uid and u.active)

    def _aic_overdue_domain(self, scope):
        today = fields.Date.context_today(self)
        if scope == "team":
            return [("user_id", "in", self._aic_team_users().ids), ("date_deadline", "<", today)]
        return [("user_id", "=", self.env.uid), ("date_deadline", "<", today)]

    @api.model
    def action_overdue(self, scope="mine"):
        """The overdue activities as a list: mine, or my team's grouped by person (Home's Missed card)."""
        team = scope == "team"
        return {
            "type": "ir.actions.act_window",
            "name": self.env._("My team's overdue activities") if team else self.env._("My overdue activities"),
            "res_model": "mail.activity",
            "views": [[False, "list"], [False, "form"]],
            "domain": self._aic_overdue_domain(scope),
            "context": {"group_by": ["user_id"]} if team else {},
            "target": "current",
        }

    def _aic_missed(self, data, ctx):
        Activity = self.env["mail.activity"]
        domain = [("user_id", "=", ctx["uid"]), ("date_deadline", "<", ctx["today"])]
        data["missed_count"] = Activity.search_count(domain)
        team = self._aic_team_users()
        if team:
            data["team_overdue_count"] = Activity.search_count([("user_id", "in", team.ids), ("date_deadline", "<", ctx["today"])])
        for act in Activity.search(domain, order="date_deadline asc, id asc", limit=6):
            days = self._days_late(act.date_deadline, ctx["today"])
            data["missed"].append({
                "id": act.id,
                "title": act.summary or act.activity_type_id.name or self.env._("Activity"),
                "sub": act.res_name or "",
                "when": self._late_label(days),
                "model": act.res_model, "res_id": act.res_id,
            })

    def _aic_today(self, data, ctx):
        rows = []
        if self._has("calendar.event"):
            partner = self.env.user.partner_id
            events = self.env["calendar.event"].search([
                ("partner_ids", "in", partner.id),
                ("start", "<", ctx["day_end"]), ("stop", ">=", ctx["day_start"]),
            ], order="start asc", limit=8)
            for ev in events:
                rows.append({"time": self.env._("All day") if ev.allday else self._fmt_time(ev.start),
                             "sort": "" if ev.allday else self._fmt_time(ev.start),
                             "title": ev.name, "sub": ev.location or "", "tone": "ok",
                             "model": "calendar.event", "res_id": ev.id, "activity_id": False})
        for act in self.env["mail.activity"].search([
            ("user_id", "=", ctx["uid"]), ("date_deadline", "=", ctx["today"]),
        ], order="id asc", limit=8):
            rows.append({"time": self.env._("To do"), "sort": "99",
                         "title": act.summary or act.activity_type_id.name or self.env._("Activity"),
                         "sub": act.res_name or "", "tone": "hot",
                         "model": act.res_model, "res_id": act.res_id, "activity_id": act.id})
        rows.sort(key=lambda r: r["sort"])
        data["today"] = rows

    # ------------------------------------------------------------------ roles
    def _aic_role_sales(self, data, ctx):
        uid, today = ctx["uid"], ctx["today"]
        if self._has("crm.lead"):
            Lead = self.env["crm.lead"]
            open_opps = [("type", "=", "opportunity"), ("user_id", "=", uid), ("won_status", "=", "pending")]
            hot_domain = open_opps + [("priority", ">=", "2")]
            hot = Lead.search(hot_domain, order="priority desc, expected_revenue desc, id desc", limit=LIMIT)
            hot_count, hot_total = self._count_sum(Lead, hot_domain, "expected_revenue")
            has_rotting = "is_rotting" in Lead._fields
            items = [self._lead_item(lead, today, has_rotting) for lead in hot]
            data["kpis"].append(self._kpi("hot", self.env._("Hot deals"), str(hot_count),
                                          self.env._("%(amount)s open", amount=self._money(hot_total)), "hot",
                                          self._action(self.env._("Hot deals"), "crm.lead", hot_domain)))
            data["panels"].append(self._panel(
                "hot", self.env._("Hot opportunities"), items, hot_count, "hot",
                self.env._("High priority, still open"),
                footer={"label": self.env._("Open the pipeline"),
                        "action": self._action(self.env._("My pipeline"), "crm.lead", open_opps)}))
            data["app_badges"]["crm.crm_menu_root"] = hot_count

            no_step_domain = open_opps + [("activity_ids", "=", False)]
            no_step = Lead.search(no_step_domain, order="expected_revenue desc, id desc", limit=LIMIT)
            no_step_count = Lead.search_count(no_step_domain)
            if no_step_count:
                data["panels"].append(self._panel(
                    "no_step", self.env._("No next step"),
                    [self._item(lead, lead.name, lead.partner_id.display_name or "",
                                self._money(lead.expected_revenue, lead.company_currency),
                                self.env._("Plan an activity"), "warn") for lead in no_step],
                    no_step_count, "warn", self.env._("Open opportunities with nothing scheduled"),
                    footer={"label": self.env._("See all"),
                            "action": self._action(self.env._("No next step"), "crm.lead", no_step_domain)}))

        if self._has("sale.order"):
            Order = self.env["sale.order"]
            expiring = [("user_id", "=", uid), ("state", "in", ("draft", "sent")),
                        ("validity_date", ">=", today), ("validity_date", "<=", today + timedelta(days=7))]
            exp_count = Order.search_count(expiring)
            data["kpis"].append(self._kpi("expiring", self.env._("Quotations expiring"), str(exp_count),
                                          self.env._("In the next 7 days"), "warn" if exp_count else "plain",
                                          self._action(self.env._("Quotations expiring"), "sale.order", expiring)))
            if exp_count:
                data["panels"].append(self._panel(
                    "expiring", self.env._("Quotations expiring this week"),
                    [self._item(o, self._join(o.name, o.partner_id.display_name), "",
                                self._money(o.amount_total, o.currency_id),
                                self.env._("Expires %(date)s", date=format_date(self.env, o.validity_date)), "warn")
                     for o in Order.search(expiring, order="validity_date asc", limit=LIMIT)],
                    exp_count, "warn", self.env._("Follow up or extend before they lapse")))
            month_start = today.replace(day=1)
            won_domain = [("user_id", "=", uid), ("state", "=", "sale"), ("date_order", ">=", month_start)]
            won_count, won_total = self._count_sum(Order, won_domain, "amount_untaxed")
            data["kpis"].append(self._kpi("won", self.env._("Confirmed this month"), self._money_short(won_total),
                                          self.env._("%(count)s orders", count=won_count), "plain",
                                          self._action(self.env._("Confirmed this month"), "sale.order", won_domain),
                                          full=self._money(won_total)))
            self._aic_cleanup_quotations(data, ctx)

        data["kpis"].append(self._kpi("overdue", self.env._("Overdue activities"), str(data["missed_count"]),
                                      self.env._("Yours"), "late" if data["missed_count"] else "plain",
                                      self._action(self.env._("My overdue activities"), "mail.activity",
                                                   [("user_id", "=", uid), ("date_deadline", "<", today)])))

    def _lead_item(self, lead, today, has_rotting):
        amount = self._money(lead.expected_revenue, lead.company_currency)
        if not lead.activity_ids:
            note, tone = self.env._("No next step"), "warn"
        elif lead.activity_date_deadline and lead.activity_date_deadline < today:
            note, tone = self._late_label(self._days_late(lead.activity_date_deadline, today)), "late"
        elif has_rotting and lead.is_rotting:
            note, tone = self.env._("Quiet %(days)s days", days=lead.rotting_days), "warn"
        else:
            note, tone = self.env._("Next: %(date)s", date=format_date(self.env, lead.activity_date_deadline)), "ok"
        return self._item(lead, lead.name, lead.partner_id.display_name or "", amount, note, tone,
                          lead.stage_id.name or "", "hot" if tone == "ok" else "plain")

    def _aic_pickings(self, code, ctx, extra=None):
        return [("picking_type_code", "=", code), ("state", "not in", ("done", "cancel", "draft"))] + (extra or [])

    def _picking_item(self, p, ctx, show_time=True):
        if p.state == "assigned":
            chip, chip_tone = self.env._("Ready"), "ok"
        elif p.state in ("confirmed", "waiting"):
            chip, chip_tone = self.env._("Waiting"), "warn"
        else:
            chip, chip_tone = dict(p._fields["state"]._description_selection(self.env)).get(p.state, p.state), "plain"
        late_days = self._days_late(p.scheduled_date, ctx["today"])
        if late_days > 0:
            note, tone = self._late_label(late_days), "late"
        else:
            note, tone = self._fmt_time(p.scheduled_date) if show_time else "", chip_tone
        return self._item(p, self._join(p.name, p.partner_id.display_name or ""), p.origin or "",
                          "", note, tone, chip, chip_tone)

    def _aic_role_warehouse(self, data, ctx):
        if not self._has("stock.picking"):
            return
        Picking = self.env["stock.picking"]
        day = [("scheduled_date", ">=", ctx["day_start"]), ("scheduled_date", "<", ctx["day_end"])]
        recent_late = [("scheduled_date", "<", ctx["day_start"]),
                       ("scheduled_date", ">=", ctx["day_start"] - timedelta(days=30))]
        older_late = [("scheduled_date", "<", ctx["day_start"] - timedelta(days=30))]
        receipts = self._aic_pickings("incoming", ctx, day)
        dispatches = self._aic_pickings("outgoing", ctx, day)
        late = [("picking_type_code", "in", ("incoming", "outgoing")),
                ("state", "not in", ("done", "cancel", "draft"))] + recent_late
        waiting = [("picking_type_code", "=", "outgoing"), ("state", "in", ("confirmed", "waiting"))]
        n_rec, n_dis = Picking.search_count(receipts), Picking.search_count(dispatches)
        n_late, n_wait = Picking.search_count(late), Picking.search_count(waiting)
        n_rec_ready = Picking.search_count(receipts + [("state", "=", "assigned")])
        n_dis_ready = Picking.search_count(dispatches + [("state", "=", "assigned")])
        data["kpis"] += [
            self._kpi("receipts", self.env._("Receipts today"), str(n_rec), self.env._("%(n)s ready", n=n_rec_ready), "hot",
                      self._action(self.env._("Receipts today"), "stock.picking", receipts)),
            self._kpi("dispatches", self.env._("Dispatches today"), str(n_dis), self.env._("%(n)s ready", n=n_dis_ready), "plain",
                      self._action(self.env._("Dispatches today"), "stock.picking", dispatches)),
            self._kpi("late", self.env._("Late transfers"), str(n_late), self.env._("Last 30 days"), "late" if n_late else "plain",
                      self._action(self.env._("Late transfers"), "stock.picking", late)),
            self._kpi("waiting", self.env._("Waiting for stock"), str(n_wait), self.env._("Deliveries"), "warn" if n_wait else "plain",
                      self._action(self.env._("Waiting for stock"), "stock.picking", waiting)),
        ]
        data["panels"].append(self._panel(
            "receipts", self.env._("Receipts today"),
            [self._picking_item(p, ctx) for p in Picking.search(receipts, order="scheduled_date asc", limit=LIMIT)],
            n_rec, "hot", self.env._("Incoming"),
            footer={"label": self.env._("All receipts"), "action": self._action(self.env._("Receipts today"), "stock.picking", receipts)}))
        data["panels"].append(self._panel(
            "dispatches", self.env._("Dispatches today"),
            [self._picking_item(p, ctx) for p in Picking.search(dispatches, order="scheduled_date asc", limit=LIMIT)],
            n_dis, "plain", self.env._("Outgoing"),
            footer={"label": self.env._("All dispatches"), "action": self._action(self.env._("Dispatches today"), "stock.picking", dispatches)}))
        if n_late:
            data["panels"].append(self._panel(
                "late", self.env._("Late transfers"),
                [self._picking_item(p, ctx, False) for p in Picking.search(late, order="scheduled_date asc", limit=LIMIT)],
                n_late, "late", self.env._("Past their scheduled date in the last 30 days"),
                footer={"label": self.env._("See all"), "action": self._action(self.env._("Late transfers"), "stock.picking", late)}))
        data["app_badges"]["stock.menu_stock_root"] = n_rec + n_dis
        self._aic_cleanup_transfers(data, ctx, older_late)
        if self._has("mrp.production"):
            self._aic_safe(self._aic_production_panels, data, ctx)

    def _aic_production_panels(self, data, ctx):
        """The planner's side of the warehouse: manufacturing orders that should have started and are not finished,
        and confirmed ones still short of components."""
        Production = self.env["mrp.production"]
        today = ctx["today"]
        late = [("state", "in", ("confirmed", "progress", "to_close")), ("date_start", "<", ctx["day_start"])]
        short = [("state", "=", "confirmed"), ("components_availability_state", "in", ("late", "unavailable"))]
        n_late, n_short = Production.search_count(late), Production.search_count(short)
        data["kpis"].append(self._kpi("mo_late", self.env._("Late manufacturing"), str(n_late), self.env._("Should have started"),
                                      "late" if n_late else "plain", self._action(self.env._("Late manufacturing orders"), "mrp.production", late)))

        def item(mo, tone):
            uom = mo.uom_id if "uom_id" in mo._fields else mo.product_uom_id   # 20: uom_id, 19: product_uom_id
            qty = "%s %s" % (int(mo.product_qty) if float(mo.product_qty).is_integer() else mo.product_qty, uom.name)
            return self._item(mo, mo.name, self._join(mo.product_id.display_name, qty), "",
                              self._late_label(self._days_late(mo.date_start, today)) if tone == "late" else "",
                              tone, mo.workorder_ids[:1].workcenter_id.display_name if "workorder_ids" in mo._fields and mo.workorder_ids else "")
        if n_late:
            data["panels"].append(self._panel(
                "mo_late", self.env._("Late manufacturing orders"),
                [item(mo, "late") for mo in Production.search(late, order="date_start asc", limit=LIMIT)],
                n_late, "late", self.env._("Should have started by now"),
                footer={"label": self.env._("See all"), "action": self._action(self.env._("Late manufacturing orders"), "mrp.production", late)}))
        if n_short:
            data["panels"].append(self._panel(
                "mo_short", self.env._("Waiting for components"),
                [item(mo, "warn") for mo in Production.search(short, order="date_start asc", limit=LIMIT)],
                n_short, "warn", self.env._("Confirmed orders short of components"),
                footer={"label": self.env._("See all"), "action": self._action(self.env._("Waiting for components"), "mrp.production", short)}))
        data["app_badges"]["mrp.menu_mrp_root"] = n_late

    def _aic_role_purchase(self, data, ctx):
        today = ctx["today"]
        if self._has("stock.picking") and "purchase_id" in self.env["stock.picking"]._fields:
            Picking = self.env["stock.picking"]
            delayed = self._aic_pickings("incoming", ctx, [("purchase_id", "!=", False),
                                                             ("scheduled_date", "<", ctx["day_start"])])
            n = Picking.search_count(delayed)
            data["kpis"].append(self._kpi("delayed", self.env._("Delayed receipts"), str(n), self.env._("Past the expected date"),
                                          "late" if n else "plain", self._action(self.env._("Delayed receipts"), "stock.picking", delayed)))
            if n:
                items = []
                for p in Picking.search(delayed, order="scheduled_date asc", limit=LIMIT):
                    items.append(self._item(p, self._join(p.purchase_id.name, p.partner_id.display_name or ""), p.name,
                                            self._money(p.purchase_id.amount_total, p.purchase_id.currency_id),
                                            self._late_label(self._days_late(p.scheduled_date, today)), "late",
                                            self.env._("Chase"), "late"))
                data["panels"].append(self._panel(
                    "delayed", self.env._("Delayed receipts"), items, n, "late", self.env._("Expected date has passed"),
                    footer={"label": self.env._("See all"), "action": self._action(self.env._("Delayed receipts"), "stock.picking", delayed)}))
        if self._has("purchase.order"):
            PO = self.env["purchase.order"]
            waiting = [("state", "=", "sent"), ("write_date", "<", ctx["day_start"] - timedelta(days=3))]
            approve = [("state", "=", "to approve")]
            n_wait, n_appr = PO.search_count(waiting), PO.search_count(approve)
            data["kpis"].append(self._kpi("rfq_wait", self.env._("RFQs awaiting reply"), str(n_wait), self.env._("Sent over 3 days ago"),
                                          "warn" if n_wait else "plain", self._action(self.env._("RFQs awaiting reply"), "purchase.order", waiting)))
            data["kpis"].append(self._kpi("to_approve", self.env._("To approve"), str(n_appr),
                                          self._money(self._count_sum(PO, approve, "amount_total")[1]),
                                          "hot" if n_appr else "plain", self._action(self.env._("To approve"), "purchase.order", approve)))
            if n_wait:
                data["panels"].append(self._panel(
                    "rfq_wait", self.env._("Waiting on vendors"),
                    [self._item(o, self._join(o.name, o.partner_id.display_name), "",
                                self._money(o.amount_total, o.currency_id),
                                self.env._("Sent %(days)s days ago", days=self._days_late(o.write_date, today)), "warn")
                     for o in PO.search(waiting, order="write_date asc", limit=LIMIT)],
                    n_wait, "warn", self.env._("RFQs sent, no answer yet")))
            data["app_badges"]["purchase.menu_purchase_root"] = n_appr + n_wait
        if self._has("stock.warehouse.orderpoint"):
            OP = self.env["stock.warehouse.orderpoint"]
            reorder = [("qty_to_order", ">", 0)]
            n = OP.search_count(reorder)
            data["kpis"].append(self._kpi("reorder", self.env._("Reorder alerts"), str(n), self.env._("Below minimum"), "plain",
                                          self._action(self.env._("Replenishment"), "stock.warehouse.orderpoint", reorder)))
            if n:
                data["panels"].append(self._panel(
                    "reorder", self.env._("Reorder suggestions"),
                    [self._item(op, op.product_id.display_name, op.warehouse_id.name or "",
                                self.env._("Order %(qty)s", qty=round(op.qty_to_order, 2)), "", "warn")
                     for op in OP.search(reorder, limit=LIMIT)],
                    n, "plain", self.env._("Stock below its minimum rule")))

    def _aic_role_accounts(self, data, ctx):
        if not self._has("account.move"):
            return
        today = ctx["today"]
        Move = self.env["account.move"]
        unpaid = [("state", "=", "posted"), ("payment_state", "in", ("not_paid", "partial"))]
        overdue_rec = [("move_type", "=", "out_invoice"), ("invoice_date_due", "<", today)] + unpaid
        bills_due = [("move_type", "=", "in_invoice"), ("invoice_date_due", "<=", today + timedelta(days=7))] + unpaid
        draft_bills = [("move_type", "=", "in_invoice"), ("state", "=", "draft")]
        n_rec, rec_total = self._count_sum(Move, overdue_rec, "amount_residual_signed")
        data["kpis"].append(self._kpi("receivables", self.env._("Overdue receivables"), self._money_short(rec_total),
                                      self.env._("%(n)s invoices", n=n_rec), "late" if n_rec else "plain",
                                      self._action(self.env._("Overdue receivables"), "account.move", overdue_rec),
                                      full=self._money(rec_total)))
        n_bills = Move.search_count(bills_due)
        data["kpis"].append(self._kpi("bills_due", self.env._("Bills due"), str(n_bills), self.env._("This week or overdue"),
                                      "warn" if n_bills else "plain", self._action(self.env._("Bills due"), "account.move", bills_due)))
        n_draft = Move.search_count(draft_bills)
        data["kpis"].append(self._kpi("draft_bills", self.env._("Bills to post"), str(n_draft), self.env._("Drafts"), "hot" if n_draft else "plain",
                                      self._action(self.env._("Bills to post"), "account.move", draft_bills)))
        if self._has("account.bank.statement.line"):
            to_rec = [("is_reconciled", "=", False)]
            n = self.env["account.bank.statement.line"].search_count(to_rec)
            data["kpis"].append(self._kpi("bank", self.env._("Bank lines to reconcile"), str(n), "", "warn" if n else "plain",
                                          self._action(self.env._("Bank lines to reconcile"), "account.bank.statement.line", to_rec)))
        if n_rec:
            top = Move.search(overdue_rec, order="amount_residual_signed desc, id desc", limit=LIMIT)
            data["panels"].append(self._panel(
                "receivables", self.env._("Overdue receivables"),
                [self._item(m, self._join(m.name, m.partner_id.display_name), "",
                            self._money(m.amount_residual_signed),
                            self._late_label(self._days_late(m.invoice_date_due, today)), "late") for m in top],
                n_rec, "late", self.env._("Largest first"),
                footer={"label": self.env._("See all"), "action": self._action(self.env._("Overdue receivables"), "account.move", overdue_rec)}))
        if n_bills:
            data["panels"].append(self._panel(
                "bills_due", self.env._("Bills due this week"),
                [self._item(m, self._join(m.name, m.partner_id.display_name), "",
                            self._money(-m.amount_residual_signed),
                            format_date(self.env, m.invoice_date_due), "late" if m.invoice_date_due < today else "warn")
                 for m in Move.search(bills_due, order="invoice_date_due asc", limit=LIMIT)],
                n_bills, "warn", self.env._("Unpaid vendor bills")))

    def _aic_role_service(self, data, ctx):
        today, uid = ctx["today"], ctx["uid"]
        if self._has("project.task"):
            Task = self.env["project.task"]
            mine = [("user_ids", "in", uid), ("is_closed", "=", False)]
            due = mine + [("date_deadline", "!=", False), ("date_deadline", "<", ctx["day_end"])]
            n_mine, n_due = Task.search_count(mine), Task.search_count(due)
            data["kpis"].append(self._kpi("tasks", self.env._("My open tasks"), str(n_mine), "", "plain",
                                          self._action(self.env._("My open tasks"), "project.task", mine)))
            data["kpis"].append(self._kpi("tasks_due", self.env._("Due or overdue"), str(n_due), self.env._("Tasks"), "late" if n_due else "plain",
                                          self._action(self.env._("Tasks due"), "project.task", due)))
            if n_due:
                items = []
                for t in Task.search(due, order="date_deadline asc", limit=LIMIT):
                    days = self._days_late(t.date_deadline, today)
                    items.append(self._item(t, t.name, t.project_id.name or "", "",
                                            self._late_label(days), "late" if days > 0 else "hot", t.stage_id.name or ""))
                data["panels"].append(self._panel("tasks_due", self.env._("My tasks: due and overdue"), items, n_due, "late"))
            data["app_badges"]["project.menu_main_pm"] = n_due
            self._aic_safe(self._aic_visits_today, data, ctx)
        if self._has("helpdesk.ticket"):
            Ticket = self.env["helpdesk.ticket"]
            open_t = [("user_id", "=", uid), ("stage_id.fold", "=", False)]
            soon = open_t + [("sla_deadline", "!=", False), ("sla_deadline", "<", ctx["day_end"])]
            n_open, n_soon = Ticket.search_count(open_t), Ticket.search_count(soon)
            data["kpis"].append(self._kpi("tickets", self.env._("My open tickets"), str(n_open), self.env._("%(n)s near their deadline", n=n_soon),
                                          "warn" if n_soon else "plain", self._action(self.env._("My open tickets"), "helpdesk.ticket", open_t)))
            if n_open:
                data["panels"].append(self._panel(
                    "tickets", self.env._("Tickets waiting on me"),
                    [self._item(t, t.name, t.partner_id.display_name or "", "",
                                self.env._("Deadline %(time)s", time=self._fmt_time(t.sla_deadline)) if t.sla_deadline else "",
                                "late" if t.sla_deadline and t.sla_deadline < ctx["day_end"] else "plain")
                     for t in Ticket.search(open_t, order="sla_deadline asc, priority desc", limit=LIMIT)],
                    n_open, "warn"))
            data["app_badges"]["helpdesk.menu_helpdesk_root"] = n_open

    def _aic_visits_today(self, data, ctx):
        """The technician's day: my open tasks at a customer's that are planned (or due) today, in visit order —
        the time, who and where. Each opens the task, which starts with its Visit card (Call, Directions)."""
        Task = self.env["project.task"]
        start, end = ctx["day_start"], ctx["day_end"]
        mine = [("user_ids", "in", ctx["uid"]), ("is_closed", "=", False), ("partner_id", "!=", False)]
        if "planned_date_begin" in Task._fields:   # Enterprise planning: the visit's start time
            today = mine + ["|", "&", ("planned_date_begin", ">=", start), ("planned_date_begin", "<", end),
                            "&", ("planned_date_begin", "=", False), "&", ("date_deadline", ">=", start), ("date_deadline", "<", end)]
            order = "planned_date_begin asc, date_deadline asc, id"
        else:
            today = mine + [("date_deadline", ">=", start), ("date_deadline", "<", end)]
            order = "date_deadline asc, id"
        n = Task.search_count(today)
        if not n:
            return
        items = []
        for t in Task.search(today, order=order, limit=LIMIT):
            when = (t.planned_date_begin if "planned_date_begin" in Task._fields else False) or t.date_deadline
            where = ", ".join(filter(None, [t.partner_id.street, t.partner_id.city]))
            items.append(self._item(t, t.partner_id.display_name, " · ".join(filter(None, [t.name, where])),
                                    self._fmt_time(when), "", "hot"))
        panel = self._panel("visits", self.env._("Today's visits"), items, n, "hot", self.env._("In visit order"))
        data["panels"].insert(0, panel)

    def _aic_role_owner(self, data, ctx):
        today = ctx["today"]
        if self._has("sale.order"):
            month = [("state", "=", "sale"), ("date_order", ">=", today.replace(day=1))]
            n_orders, sales_total = self._count_sum(self.env["sale.order"], month, "amount_untaxed")
            data["kpis"].append(self._kpi("sales_month", self.env._("Sales this month"), self._money_short(sales_total),
                                          self.env._("%(n)s orders", n=n_orders), "hot", self._action(self.env._("Sales this month"), "sale.order", month)))
        if self._has("crm.lead"):
            pipe = [("type", "=", "opportunity"), ("won_status", "=", "pending")]
            n_leads, pipe_total = self._count_sum(self.env["crm.lead"], pipe, "expected_revenue")
            data["kpis"].append(self._kpi("pipeline", self.env._("Open pipeline"), self._money_short(pipe_total),
                                          self.env._("%(n)s opportunities", n=n_leads), "plain", self._action(self.env._("Open pipeline"), "crm.lead", pipe)))
        sub = {"kpis": [], "panels": [], "app_badges": {}, "missed_count": data["missed_count"]}
        if self._has("account.move"):
            self._aic_safe(self._aic_owner_cash, data, ctx)
            self._aic_safe(self._aic_role_accounts, sub, ctx)
            # money in and out: what customers owe past due and the bills to pay this week
            data["kpis"] += [k for k in sub["kpis"] if k["key"] in ("receivables", "bills_due")]
            data["panels"] += [p for p in sub["panels"] if p["key"] in ("receivables", "bills_due")]
        if self._has("stock.picking"):
            sub = {"kpis": [], "panels": [], "app_badges": {}, "missed_count": 0}
            self._aic_safe(self._aic_role_warehouse, sub, ctx)
            data["kpis"] += [k for k in sub["kpis"] if k["key"] == "late"]
            data["panels"] += [p for p in sub["panels"] if p["key"] in ("late", "cleanup_transfers")]
        if self._has("crm.lead"):
            Lead = self.env["crm.lead"]
            hot = [("type", "=", "opportunity"), ("won_status", "=", "pending"), ("priority", ">=", "2")]
            n = Lead.search_count(hot)
            if n:
                data["panels"].append(self._panel(
                    "hot_all", self.env._("Hot opportunities (all)"),
                    [self._lead_item(l, today, "is_rotting" in Lead._fields)
                     for l in Lead.search(hot, order="expected_revenue desc", limit=LIMIT)],
                    n, "hot", self.env._("Across the team")))

    def _aic_owner_cash(self, data, ctx):
        """Cash and bank as the Accounting dashboard shows it: each bank's running balance from its statement lines
        (the bank's own figure), or the ledger balance for a journal without any; in the company currency."""
        if not self._has("account.journal"):
            return
        journals = self.env["account.journal"].search([("type", "in", ("bank", "cash")), ("company_id", "in", self.env.companies.ids)])
        if not journals:
            return
        company = self.env.company
        ledger = dict(self.env["account.move.line"]._read_group(
            [("account_id", "in", journals.default_account_id.ids), ("parent_state", "=", "posted"),
             ("company_id", "in", self.env.companies.ids)], ["account_id"], ["balance:sum"]))
        total = 0.0
        for journal in journals:
            if journal.has_statement_lines:
                amount, currency = journal.current_statement_balance, journal.currency_id or journal.company_id.currency_id
            else:   # ledger balances are in the journal's company currency
                amount, currency = ledger.get(journal.default_account_id, 0.0) or 0.0, journal.company_id.currency_id
            total += currency._convert(amount, company.currency_id, company, ctx["today"]) if currency != company.currency_id else amount
        data["kpis"].append(self._kpi("cash", self.env._("Cash and bank"), self._money_short(total),
                                      self.env._("1 account") if len(journals) == 1 else self.env._("%(n)s accounts", n=len(journals)),
                                      "late" if total < 0 else "plain",
                                      # the Accounting dashboard, where each bank shows its balance and lines to reconcile
                                      dict(self._action(self.env._("Cash and bank"), "account.journal", [("id", "in", journals.ids)]),
                                           xmlid="account.open_account_journal_dashboard_kanban"),
                                      full=self._money(total)))

    # ------------------------------------------------------------------ backlog clean-up prompts
    def _aic_cleanup_quotations(self, data, ctx):
        if not self.env.user.has_group("sales_team.group_sale_manager"):
            return
        stale = [("state", "in", ("draft", "sent")),
                 ("create_date", "<", ctx["day_start"] - timedelta(days=60))]
        n = self.env["sale.order"].search_count(stale)
        if n >= 10:
            data["panels"].append(self._panel(
                "cleanup_quotations", self.env._("Old quotations"), [], n, "warn",
                self.env._("%(n)s quotations older than 60 days are still open. Clearing them keeps these "
                           "numbers meaningful.", n=n),
                cleanup={"kind": "quotations", "label": self.env._("Clean up old quotations")}))

    def _aic_cleanup_transfers(self, data, ctx, older_late):
        if not self.env.user.has_group("stock.group_stock_manager"):
            return
        older = [("picking_type_code", "in", ("incoming", "outgoing")),
                 ("state", "not in", ("done", "cancel", "draft"))] + older_late
        n = self.env["stock.picking"].search_count(older)
        if n:
            data["panels"].append(self._panel(
                "cleanup_transfers", self.env._("Older backlog"), [], n, "warn",
                self.env._("%(n)s transfers are more than 30 days past their date. They are left out of the "
                           "counts above.", n=n),
                cleanup={"kind": "deliveries", "label": self.env._("Clean up late transfers")}))

    # ------------------------------------------------------------------ summary sentence
    def _aic_summary(self, data, role):
        parts = []
        missed, today_n = data["missed_count"], len(data["today"])
        if missed and today_n:
            parts.append(self.env._("You have %(missed)s missed and %(today)s due today.", missed=missed, today=today_n))
        elif missed:
            parts.append(self.env._("You have %(missed)s missed to catch up on.", missed=missed))
        elif today_n:
            parts.append(self.env._("1 thing is on your list today.") if today_n == 1
                         else self.env._("%(today)s things are on your list today.", today=today_n))
        else:
            parts.append(self.env._("Nothing is overdue and nothing is due today."))
        panels = {p["key"]: p for p in data["panels"]}
        kpis = {k["key"]: k for k in data["kpis"]}
        if role == "sales":
            quiet = [i for i in panels.get("hot", {}).get("items", []) if i["tone"] in ("warn", "late")]
            if quiet:
                parts.append(self.env._("%(n)s of your hot deals need attention.", n=len(quiet)))
            if "no_step" in panels:
                n = panels["no_step"]["badge"]
                parts.append(self.env._("1 opportunity has no next step.") if str(n) == "1"
                             else self.env._("%(n)s opportunities have no next step.", n=n))
        elif role == "warehouse":
            if "receipts" in kpis:
                parts.append(self.env._("%(r)s receipts and %(d)s dispatches are planned today.",
                               r=kpis["receipts"]["value"], d=kpis["dispatches"]["value"]))
        elif role == "purchase" and "delayed" in kpis and kpis["delayed"]["value"] != "0":
            n = kpis["delayed"]["value"]
            parts.append(self.env._("1 receipt is late from its vendor.") if n == "1"
                         else self.env._("%(n)s receipts are late from vendors.", n=n))
        elif role == "accounts" and "receivables" in kpis:
            parts.append(self.env._("Overdue receivables stand at %(amount)s.", amount=kpis["receivables"]["value"]))
        elif role == "service" and "tasks_due" in kpis and kpis["tasks_due"]["value"] != "0":
            parts.append(self.env._("%(n)s of your tasks are due or overdue.", n=kpis["tasks_due"]["value"]))
        if data.get("approvals_count"):
            parts.append(self.env._("%(n)s waiting for your approval.", n=data["approvals_count"]))
        if data.get("for_you_count"):
            parts.append(self.env._("1 message is waiting for you.") if data["for_you_count"] == 1
                         else self.env._("%(n)s messages are waiting for you.", n=data["for_you_count"]))
        if data.get("failed_count"):
            parts.append(self.env._("%(n)s of your sends did not go out.", n=data["failed_count"]))
        return " ".join(parts)
