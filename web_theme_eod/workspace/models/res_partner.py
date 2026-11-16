# -*- coding: utf-8 -*-
import re

from odoo import api, fields, models
from odoo.tools import email_normalize, format_amount, format_date

DUPLICATES_SHOWN = 5


class ResPartner(models.Model):
    _inherit = "res.partner"

    # Odoo warns about a duplicate only when the tax ID matches. Contacts are mostly created from a name, an
    # e-mail and a phone, so the form also names the contacts that already have the same e-mail address or
    # the same phone number (both normalised), leaving out the contact's own company and its people.
    aic_duplicate_ids = fields.Many2many(
        "res.partner", string="Possible duplicates", compute="_compute_aic_duplicate_ids",
        help="Other contacts with the same e-mail address or phone number.",
    )

    def _aic_phone_key(self, number):
        """E.164 when the number can be read for the contact's country, else its digits."""
        if not number:
            return False
        formatter = getattr(self, "_phone_format", None)
        formatted = formatter(number=number, raise_exception=False) if formatter else False
        return formatted or re.sub(r"\D", "", number) or False

    @api.depends("email", "phone", "parent_id", "country_id")
    def _compute_aic_duplicate_ids(self):
        for partner in self:
            email = email_normalize(partner.email) if partner.email else False
            phone = partner._aic_phone_key(partner.phone)
            if not email and not (phone and len(re.sub(r"\D", "", phone)) >= 6):
                partner.aic_duplicate_ids = False
                continue
            clauses = []
            if email:
                clauses.append([("email_normalized", "=", email)])
            if phone and len(re.sub(r"\D", "", phone)) >= 6:
                clauses.append([("phone_sanitized", "=", phone)])
            domain = clauses[0] if len(clauses) == 1 else ["|", *clauses[0], *clauses[1]]
            own = partner._origin.id
            family = partner.parent_id.commercial_partner_id or partner._origin.commercial_partner_id
            if own:
                domain = [("id", "!=", own), *domain]
            if family:
                domain = [("commercial_partner_id", "!=", family.id), *domain]
            partner.aic_duplicate_ids = self.search(domain, limit=DUPLICATES_SHOWN)

    # ------------------------------------------------------------------ customer overview
    def aic_customer_overview(self):
        """The contact's company at a glance, for the strip at the top of the contact form: open quotations,
        unpaid invoices (and how many are overdue), open tickets, the last delivery and the next activity. Each
        source only when its app is installed and the user can read it; empty sources are left out."""
        self.ensure_one()
        env, partner = self.env, self.commercial_partner_id
        family = [("partner_id", "child_of", partner.id)]
        today = fields.Date.context_today(self)
        chips = []

        def readable(model):
            return model in env and env[model].has_access("read")

        def money(amount, currency):
            return format_amount(env, amount, currency or env.company.currency_id)

        if readable("sale.order"):
            dom = family + [("state", "in", ("draft", "sent"))]
            groups = env["sale.order"]._read_group(dom, ["currency_id"], ["__count", "amount_total:sum"])
            n = sum(c for _cur, c, _a in groups)
            if n:
                # one currency: its total; several: the count only (amounts in different currencies do not add up)
                note = money(groups[0][2], groups[0][0]) if len(groups) == 1 else ""
                chips.append({"key": "quotations", "label": env._("Open quotations"), "value": str(n),
                              "note": note, "tone": "plain",
                              "action": {"res_model": "sale.order", "domain": dom, "name": env._("Open quotations")}})
        if readable("account.move"):
            dom = family + [("move_type", "=", "out_invoice"), ("state", "=", "posted"),
                            ("payment_state", "in", ("not_paid", "partial"))]
            n = env["account.move"].search_count(dom)
            if n:
                late = env["account.move"].search_count(dom + [("invoice_date_due", "<", today)])
                groups = env["account.move"]._read_group(dom, ["currency_id"], ["amount_residual:sum"])
                note = money(groups[0][1], groups[0][0]) if len(groups) == 1 else ""
                if late and note:
                    note = env._("%(amount)s · %(late)s overdue", amount=note, late=late)
                elif late:
                    note = env._("%(late)s overdue", late=late)
                chips.append({"key": "invoices", "label": env._("Unpaid invoices"), "value": str(n), "note": note,
                              "tone": "late" if late else "warn",
                              "action": {"res_model": "account.move", "domain": dom, "name": env._("Unpaid invoices")}})
        if readable("helpdesk.ticket"):
            dom = family + [("stage_id.fold", "=", False)]
            n = env["helpdesk.ticket"].search_count(dom)
            if n:
                chips.append({"key": "tickets", "label": env._("Open tickets"), "value": str(n), "note": "",
                              "tone": "warn", "action": {"res_model": "helpdesk.ticket", "domain": dom, "name": env._("Open tickets")}})
        if readable("stock.picking"):
            dom = family + [("picking_type_code", "=", "outgoing"), ("state", "=", "done")]
            last = env["stock.picking"].search(dom, order="date_done desc", limit=1)
            if last:
                chips.append({"key": "delivery", "label": env._("Last delivery"),
                              "value": format_date(env, last.date_done.date()), "note": last.name, "tone": "plain",
                              "action": {"res_model": "stock.picking", "res_id": last.id, "name": last.name}})
        act = env["mail.activity"].search([("res_model", "=", "res.partner"), ("res_id", "in", (self | partner).ids)],
                                          order="date_deadline asc", limit=1)
        if act:
            chips.append({"key": "activity", "label": env._("Next activity"), "value": format_date(env, act.date_deadline),
                          "note": act.summary or act.activity_type_id.name or "",
                          "tone": "late" if act.date_deadline < today else "plain", "action": False})
        return chips
