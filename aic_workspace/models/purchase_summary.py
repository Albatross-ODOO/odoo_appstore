# -*- coding: utf-8 -*-
"""Purchase orders in plain words, without a dependency on Purchase (asked by the web client only on a purchase
order): the lines late from the vendor, the sales orders they hold up, and a Chase vendor e-mail."""
from odoo import api, fields, models


class AicPurchaseSummary(models.AbstractModel):
    _name = "aic.purchase.summary"
    _description = "Core: purchase summaries"

    @staticmethod
    def _qty(qty):
        return str(int(qty)) if float(qty).is_integer() else str(round(qty, 2))

    def _purchase(self, order_id):
        if "purchase.order" not in self.env:
            return False
        order = self.env["purchase.order"].browse(int(order_id)).exists()
        return order if order and order.has_access("read") else False

    @api.model
    def purchase_late(self, order_id):
        """Lines past their expected date with quantities still to receive (confirmed orders only)."""
        order = self._purchase(order_id)
        if not order or order.state != "purchase":
            return False
        now = fields.Datetime.now()
        lines = []
        for line in order.order_line.filtered(lambda l: not l.display_type and l.date_planned and l.date_planned < now):
            left = line.product_qty - line.qty_received
            if left <= 1e-6:
                continue
            uom = line.uom_id if "uom_id" in line._fields else line.product_uom_id   # 20: uom_id, 19: product_uom_id
            lines.append({
                "product": line.product_id.display_name or line.name,
                "left": self._qty(left), "ordered": self._qty(line.product_qty), "uom": uom.name,
                "days": (now.date() - line.date_planned.date()).days,
            })
        if not lines:
            return False
        # the sales orders these purchases feed (Sales + Purchase installed: Odoo's own link)
        sales = order._get_sale_orders() if hasattr(order, "_get_sale_orders") else []
        sales = sales.filtered(lambda s: s.has_access("read") and s.state != "cancel") if sales else []
        return {
            "lines": lines[:8], "more": max(0, len(lines) - 8),
            "sales": [{"id": s.id, "name": s.name, "customer": s.partner_id.display_name} for s in sales][:5],
            "can_chase": bool(self.env.ref("purchase.email_template_edi_purchase_reminder", raise_if_not_found=False)),
        }

    @api.model
    def chase_vendor_action(self, order_id):
        """Odoo's own composer with its reminder template, addressed to the vendor."""
        order = self._purchase(order_id)
        template = self.env.ref("purchase.email_template_edi_purchase_reminder", raise_if_not_found=False)
        if not order or not template:
            return False
        return {
            "type": "ir.actions.act_window", "res_model": "mail.compose.message", "view_mode": "form",
            "views": [[False, "form"]], "target": "new", "name": self.env._("Chase vendor"),
            "context": {"default_model": "purchase.order", "default_res_ids": order.ids, "default_template_id": template.id,
                        "default_composition_mode": "comment", "default_email_layout_xmlid": "mail.mail_notification_layout_with_responsible_signature",
                        "force_email": True},
        }
