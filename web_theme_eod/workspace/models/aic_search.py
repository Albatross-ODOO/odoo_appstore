# -*- coding: utf-8 -*-
"""Records in the command palette (Ctrl+K): type a name and the matching contacts, opportunities,
quotations, invoices, purchase orders, transfers, tasks, tickets and products appear under the commands.

One call per search. Each model is searched with Odoo's own ``name_search`` (the same matching as a
many2one field), only for models the user may read and with their record rules, a few results per model.
Every result carries a short kind ("Quotation", "Invoice") and a hint (the customer, the amount) so two
records with the same name can be told apart. Models of apps that are not installed are skipped.
"""
from odoo import api, models
from odoo.exceptions import AccessError
from odoo.tools.misc import format_amount

PER_MODEL = 4
TOTAL = 12
MIN_TERM = 2


class AicSearch(models.AbstractModel):
    _name = "aic.search"
    _description = "Core record search (command palette)"

    def _aic_search_sources(self):
        """[(model, domain, kind(record) -> str, hint(record) -> str)]; other modules may extend it."""
        _ = self.env._
        money = lambda rec, field="amount_total": (format_amount(self.env, rec[field], rec.currency_id)
                                                   if "currency_id" in rec._fields and rec.currency_id else "")
        partner = lambda rec: rec.partner_id.display_name or "" if "partner_id" in rec._fields else ""
        join = lambda *parts: " · ".join(p for p in parts if p)
        move_kinds = {"out_invoice": _("Invoice"), "out_refund": _("Credit note"),
                      "in_invoice": _("Vendor bill"), "in_refund": _("Vendor refund")}
        return [
            # (Odoo 20 sets is_company from a valid VAT number: a partner with contacts under it is a company too)
            ("res.partner", [], lambda r: _("Company") if r.is_company or (not r.parent_id and r.child_ids) else _("Contact"),
             lambda r: join(r.parent_id.name or "", r.email or r.city or "")),
            ("crm.lead", [], lambda r: _("Opportunity") if r.type == "opportunity" else _("Lead"),
             lambda r: join(r.partner_id.display_name or r.partner_name or "", r.stage_id.name or "")),
            ("sale.order", [], lambda r: _("Quotation") if r.state in ("draft", "sent") else _("Sales order"),
             lambda r: join(partner(r), money(r))),
            ("account.move", [("move_type", "in", list(move_kinds))], lambda r: move_kinds.get(r.move_type, _("Invoice")),
             lambda r: join(partner(r), money(r))),
            ("purchase.order", [], lambda r: _("Request for quotation") if r.state in ("draft", "sent", "to approve") else _("Purchase order"),
             lambda r: join(partner(r), money(r))),
            ("stock.picking", [], lambda r: _("Transfer"), lambda r: join(partner(r), r.origin or "")),
            ("project.task", [], lambda r: _("Task"), lambda r: r.project_id.name or ""),
            ("helpdesk.ticket", [], lambda r: _("Ticket"), lambda r: partner(r)),
            ("product.template", [], lambda r: _("Product"), lambda r: r.categ_id.display_name or ""),
        ]

    @api.model
    def search_records(self, term):
        term = (term or "").strip()
        if len(term) < MIN_TERM:
            return []
        results = []
        for model, domain, kind, hint in self._aic_search_sources():
            if len(results) >= TOTAL or model not in self.env:
                continue
            Model = self.env[model]
            try:
                if not Model.has_access("read"):
                    continue
                found = Model.name_search(term, domain=domain, limit=PER_MODEL)
                records = Model.browse([rid for rid, _name in found])
                for record in records:
                    results.append({"model": model, "id": record.id, "name": record.display_name,
                                    "kind": kind(record), "hint": hint(record)})
            except AccessError:
                continue
        return results[:TOTAL]
