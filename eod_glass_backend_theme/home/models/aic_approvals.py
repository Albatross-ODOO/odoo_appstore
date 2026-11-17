# -*- coding: utf-8 -*-
"""To approve: one Home panel, for every role, listing what waits for the current user's approval in the apps that
are installed, with an Approve key on each row.

Sources (each only when its app is installed and the user is the one who approves):
* purchase orders waiting for the second validation (purchase managers);
* requests in Odoo's Approvals app where the user is a pending approver (Enterprise);
* time off whose employee has the user as time-off approver;
* expenses (or, on older versions, expense reports) submitted to the user as manager.

Refuse asks for a reason in the row itself; the reason goes to the record's chatter (and, for expenses, through
Odoo's own refuse wizard, which records it on the expense).
"""
from odoo import api, models
from odoo.exceptions import AccessError, UserError

APPROVALS_SHOWN = 6


class AicHomeApprovals(models.AbstractModel):
    _inherit = "aic.home"

    # ------------------------------------------------------------------ sources
    def _aic_approval_sources(self):
        """[(model, domain, approve_method)] the current user can approve, for the installed apps."""
        env, uid, sources = self.env, self.env.uid, []
        if "purchase.order" in env and env.user.has_group("purchase.group_purchase_manager"):
            sources.append(("purchase.order", [("state", "=", "to approve")], "button_approve"))
        if "approval.approver" in env:
            reqs = env["approval.approver"].search([("user_id", "=", uid), ("status", "=", "pending")]).request_id
            reqs = reqs.filtered(lambda r: r.request_status == "pending")
            sources.append(("approval.request", [("id", "in", reqs.ids)], "action_approve"))
        if "hr.leave" in env and "leave_manager_id" in env["hr.employee"]._fields:
            sources.append(("hr.leave", [("state", "=", "confirm"), ("employee_id.leave_manager_id", "=", uid)],
                            "action_approve"))
        if "hr.expense.sheet" in env:
            sources.append(("hr.expense.sheet", [("state", "=", "submit"), ("user_id", "=", uid)], "action_approve_expense_sheets"))
        elif "hr.expense" in env and "manager_id" in env["hr.expense"]._fields:
            # 19 and 20 approve expenses one by one (no reports)
            sources.append(("hr.expense", [("state", "=", "submitted"), ("manager_id", "=", uid)], "action_approve"))
        return sources

    def _aic_approval_item(self, rec):
        title, sub, right = rec.display_name, "", ""
        if rec._name == "purchase.order":
            sub = rec.partner_id.display_name or ""
            right = self._money(rec.amount_total, rec.currency_id)
        elif rec._name == "approval.request":
            sub = rec.request_owner_id.name or ""
        elif rec._name == "hr.leave":
            sub = rec.employee_id.name or ""
            right = self.env._("%(days)s days", days=("%g" % rec.number_of_days)) if "number_of_days" in rec._fields else ""
        elif rec._name in ("hr.expense.sheet", "hr.expense"):
            sub = rec.employee_id.name or ""
            if "total_amount_currency" in rec._fields:     # the amount as spent, in its own currency
                right = self._money(rec.total_amount_currency, rec.currency_id)
            elif "total_amount" in rec._fields:
                right = self._money(rec.total_amount, rec.currency_id)
        kind = self.env["ir.model"]._get(rec._name).name
        item = self._item(rec, title, self._join(kind, sub), right, "", "warn")
        item["approve"] = True
        return item

    def _aic_approvals(self, data, ctx):
        rows, total = [], 0
        for model, domain, _method in self._aic_approval_sources():
            Model = self.env[model]
            if not Model.has_access("read"):
                continue
            n = Model.search_count(domain)
            total += n
            for rec in Model.search(domain, order="id asc", limit=APPROVALS_SHOWN):
                rows.append(self._aic_approval_item(rec))
        data["approvals_count"] = total
        if not total:
            return
        data["kpis"].insert(0, self._kpi("approvals", self.env._("To approve"), str(total),
                                         self.env._("Waiting for you"), "hot"))
        data["panels"].insert(0, self._panel(
            "approvals", self.env._("To approve"), rows[:APPROVALS_SHOWN], total, "warn",
            self.env._("Waiting for your approval")))

    # ------------------------------------------------------------------ the Approve key
    @api.model
    def approve_item(self, model, res_id):
        """Approve one row of the panel: only a record that is in one of the user's own sources, with that
        source's own approve method (Odoo's checks run as the user)."""
        for src_model, domain, method in self._aic_approval_sources():
            if src_model != model:
                continue
            rec = self.env[model].search([("id", "=", int(res_id))] + domain, limit=1)
            if not rec:
                break
            getattr(rec, method)()
            return self.env._("%(name)s approved", name=rec.display_name)
        raise UserError(self.env._("This record no longer waits for your approval."))

    # ------------------------------------------------------------------ the Refuse key
    def _aic_refuse(self, rec, reason):
        """Refuse one record the Odoo way for its kind; the reason is always recorded."""
        if rec._name == "hr.expense" and "hr.expense.refuse.wizard" in self.env:
            rec._check_can_refuse()
            self.env["hr.expense.refuse.wizard"].create({"reason": reason, "expense_ids": [(6, 0, rec.ids)]}).action_refuse()
            return
        if rec._name == "purchase.order":
            rec.button_cancel()
        elif hasattr(rec, "action_refuse"):
            rec.action_refuse()
        else:
            raise UserError(self.env._("This record cannot be refused from Home."))
        rec.message_post(body=self.env._("Refused: %(reason)s", reason=reason))

    @api.model
    def refuse_item(self, model, res_id, reason):
        """Refuse one row of the panel with a reason: only a record that is in one of the user's own sources."""
        reason = (reason or "").strip()
        if not reason:
            raise UserError(self.env._("Give a reason to refuse."))
        for src_model, domain, _method in self._aic_approval_sources():
            if src_model != model:
                continue
            rec = self.env[model].search([("id", "=", int(res_id))] + domain, limit=1)
            if not rec:
                break
            self._aic_refuse(rec, reason)
            return self.env._("%(name)s refused", name=rec.display_name)
        raise UserError(self.env._("This record no longer waits for your approval."))
