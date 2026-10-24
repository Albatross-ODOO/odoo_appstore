# -*- coding: utf-8 -*-
from datetime import timedelta

from markupsafe import Markup

from odoo import api, fields, models
from odoo.exceptions import AccessError, UserError

KINDS = [
    ("quotations", "Old quotations"),
    ("deliveries", "Late deliveries"),
    ("receipts", "Late receipts"),
]
# who may run each clean-up, and which model it touches
KIND_RULES = {
    "quotations": ("sale.order", "sales_team.group_sale_manager"),
    "deliveries": ("stock.picking", "stock.group_stock_manager"),
    "receipts": ("stock.picking", "stock.group_stock_manager"),
}


class AicBacklogCleanup(models.TransientModel):
    _name = "aic.backlog.cleanup"
    _description = "Core backlog clean-up"

    kind = fields.Selection(KINDS, string="Clean up", required=True, default="quotations")
    older_than_days = fields.Integer(string="Older than (days)", required=True, default=60)
    operation = fields.Selection([
        ("cancel", "Cancel them"),
        ("reschedule", "Move them to a new date"),
    ], string="What to do", required=True, default="cancel")
    new_date = fields.Date(string="New date", default=lambda self: fields.Date.context_today(self) + timedelta(days=1))
    confirm = fields.Boolean(string="I have checked the list and want to go ahead")
    match_count = fields.Integer(compute="_compute_preview")
    preview_html = fields.Html(compute="_compute_preview", sanitize=False)

    @api.onchange("kind")
    def _onchange_kind(self):
        if self.kind == "quotations":
            self.older_than_days, self.operation = 60, "cancel"
        else:
            self.older_than_days, self.operation = 30, "reschedule"

    def _model_and_domain(self):
        self.ensure_one()
        model, _group = KIND_RULES[self.kind]
        if model not in self.env:
            return None, []
        limit = fields.Datetime.now() - timedelta(days=max(self.older_than_days, 1))
        if self.kind == "quotations":
            return model, [("state", "in", ("draft", "sent")), ("create_date", "<", limit)]
        code = "outgoing" if self.kind == "deliveries" else "incoming"
        return model, [("picking_type_code", "=", code), ("state", "not in", ("done", "cancel", "draft")),
                       ("scheduled_date", "<", limit)]

    @api.depends("kind", "older_than_days")
    def _compute_preview(self):
        for wizard in self:
            model, domain = wizard._model_and_domain() if wizard.kind else (None, [])
            if not model:
                wizard.match_count = 0
                wizard.preview_html = Markup("<p>%s</p>") % self.env._("This clean-up needs an app that is not installed.")
                continue
            records = self.env[model].search(domain, order="id asc", limit=12)
            wizard.match_count = self.env[model].search_count(domain)
            rows = Markup("").join(
                Markup("<li>%s</li>") % ("%s · %s" % (r.display_name, r.partner_id.display_name or "")) for r in records)
            more = wizard.match_count - len(records)
            tail = Markup("<li>%s</li>") % self.env._("…and %(n)s more", n=more) if more > 0 else Markup("")
            wizard.preview_html = (Markup("<p><b>%s</b></p><ul>%s%s</ul>")
                                   % (self.env._("%(n)s records match.", n=wizard.match_count), rows, tail))

    def _check_rights(self):
        _model, group = KIND_RULES[self.kind]
        if not self.env.user.has_group(group):
            raise AccessError(self.env._("Only managers of this area can run this clean-up."))

    def action_open_list(self):
        self.ensure_one()
        model, domain = self._model_and_domain()
        return {"type": "ir.actions.act_window", "name": dict(KINDS)[self.kind], "res_model": model,
                "domain": domain, "views": [(False, "list"), (False, "form")], "target": "current"}

    def action_apply(self):
        self.ensure_one()
        self._check_rights()
        if not self.confirm:
            raise UserError(self.env._("Tick the box to confirm you have checked the list."))
        model, domain = self._model_and_domain()
        if not model:
            raise UserError(self.env._("This clean-up needs an app that is not installed."))
        records = self.env[model].search(domain)
        if not records:
            raise UserError(self.env._("Nothing matches any more; there is nothing to clean up."))
        if self.operation == "reschedule":
            if self.kind == "quotations":
                raise UserError(self.env._("Quotations can only be cancelled here."))
            if not self.new_date:
                raise UserError(self.env._("Choose the new date."))
            records.write({"scheduled_date": fields.Datetime.to_datetime(self.new_date)})
            message = self.env._("%(n)s transfers moved to %(date)s.", n=len(records), date=self.new_date)
        else:
            records.action_cancel()
            message = self.env._("%(n)s records cancelled.", n=len(records))
        return {
            "type": "ir.actions.client", "tag": "display_notification",
            "params": {"title": self.env._("Backlog cleaned up"), "message": message, "type": "success",
                       "next": {"type": "ir.actions.act_window_close"}},
        }
