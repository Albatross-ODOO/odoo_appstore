# -*- coding: utf-8 -*-
from datetime import timedelta

from odoo import api, fields, models

HOME_ROLES = [
    ("auto", "Suggest from activity"),
    ("sales", "Sales"),
    ("warehouse", "Warehouse"),
    ("purchase", "Purchase"),
    ("accounts", "Accounts"),
    ("service", "Service"),
    ("owner", "Owner / manager"),
]
ROLE_LABELS = dict(HOME_ROLES)


class ResUsers(models.Model):
    _inherit = "res.users"

    aic_home_role = fields.Selection(
        HOME_ROLES, string="Home role", default="auto", required=True,
        help="Decides which panels the Home shows first. \"Suggest from activity\" picks the role from "
             "what the person worked on in the last 90 days. This never changes access rights.")
    aic_home_role_suggested = fields.Selection(
        HOME_ROLES[1:], string="Suggested role", compute="_compute_aic_home_role_suggested",
        help="The role \"Suggest from activity\" would pick today.")

    aic_home_layout = fields.Json(
        string="Home layout", copy=False, groups="base.group_system",
        help="What each person chose in Customise home, per role: {role: {hidden: [keys], order: [keys]}}. "
             "Written only through aic.home.save_layout / reset_layout, for the current user.")
    aic_home_failed_seen = fields.Datetime(
        string="Failed sends dismissed until", copy=False, groups="base.group_system",
        help="Home's \"Failed to send\" panel shows no WhatsApp failure older than this (Dismiss). E-mail and "
             "text-message failures are dismissed the Odoo way instead. Written only by aic.home.")

    @api.depends("aic_home_role")
    def _compute_aic_home_role_suggested(self):
        for user in self:
            user.aic_home_role_suggested = user._aic_suggest_role()

    def _aic_effective_role(self):
        self.ensure_one()
        return self.aic_home_role if self.aic_home_role != "auto" else self._aic_suggest_role()

    def _aic_suggest_role(self):
        """The role matching what this user created or owns most in the last 90 days.

        Counted with sudo on purpose: it only measures this user's own footprint, and returns a role name,
        never records. Ties and empty histories fall back to the user's groups.
        """
        self.ensure_one()
        env = self.env(su=True)
        since = fields.Datetime.now() - timedelta(days=90)
        uid = self.id
        score = dict.fromkeys(("sales", "warehouse", "purchase", "accounts", "service"), 0)

        def count(model, domain):
            if model not in env:
                return 0
            return env[model].search_count(domain)

        score["sales"] += count("crm.lead", [("user_id", "=", uid), ("create_date", ">=", since)])
        score["sales"] += count("sale.order", [("user_id", "=", uid), ("create_date", ">=", since)])
        score["warehouse"] += count("stock.picking", [("write_uid", "=", uid), ("date_done", ">=", since)])
        score["purchase"] += 2 * count("purchase.order", [("user_id", "=", uid), ("create_date", ">=", since)])
        score["accounts"] += count("account.move", [
            ("create_uid", "=", uid), ("create_date", ">=", since),
            ("move_type", "in", ("out_invoice", "in_invoice", "out_refund", "in_refund"))])
        score["service"] += count("project.task", [("user_ids", "in", uid), ("create_date", ">=", since)])
        score["service"] += count("helpdesk.ticket", [("user_id", "=", uid), ("create_date", ">=", since)])

        best = max(score, key=score.get)
        if score[best] > 0:
            return best
        # nothing to go on: use the strongest manager group the user has
        for xmlid, role in (
            ("account.group_account_manager", "accounts"),
            ("stock.group_stock_manager", "warehouse"),
            ("purchase.group_purchase_manager", "purchase"),
            ("sales_team.group_sale_salesman", "sales"),
        ):
            group = self.env.ref(xmlid, raise_if_not_found=False)
            if group and group in self.all_group_ids:
                return role
        return "owner"
