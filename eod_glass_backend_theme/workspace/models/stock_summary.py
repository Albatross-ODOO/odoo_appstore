# -*- coding: utf-8 -*-
"""Plain-language stock summaries for transfers, without a dependency on Inventory (the web client asks only when
the transfer or the backorder dialog is on screen): what a transfer still waits for, and what a backorder would
carry."""
from odoo import api, fields, models

WAITING_STATES = ("confirmed", "waiting", "partially_available")


class AicStockSummary(models.AbstractModel):
    _name = "aic.stock.summary"
    _description = "Core: stock summaries"

    @staticmethod
    def _uom(move):
        # Odoo 20 names the move's unit uom_id, 19 product_uom
        return move.uom_id if "uom_id" in move._fields else move.product_uom

    @staticmethod
    def _qty(qty):
        return str(int(qty)) if float(qty).is_integer() else str(round(qty, 2))

    @api.model
    def picking_missing(self, picking_id):
        """A delivery or internal transfer that waits for stock: the products not available yet, how many of how many,
        and when Odoo expects them. False when nothing is missing, for receipts, or when the user may not read it."""
        if "stock.picking" not in self.env:
            return False
        picking = self.env["stock.picking"].browse(int(picking_id)).exists()
        if not picking or not picking.has_access("read") or picking.state not in ("confirmed", "waiting", "assigned"):
            return False
        if picking.picking_type_code == "incoming":
            return False
        rows = []
        for move in picking.move_ids.filtered(lambda m: m.state in WAITING_STATES):
            missing = move.product_uom_qty - move.quantity
            if missing <= 1e-6:
                continue
            rows.append({
                "product": move.product_id.display_name,
                "missing": self._qty(missing),
                "demand": self._qty(move.product_uom_qty),
                "uom": self._uom(move).name,
                "expected": fields.Date.to_string(move.forecast_expected_date.date()) if move.forecast_expected_date else False,
            })
        return rows or False

    @api.model
    def backorder_summary(self, picking_ids):
        """What the backorder dialog is about, per product: the quantities still to process on these transfers."""
        if "stock.picking" not in self.env or not picking_ids:
            return False
        pickings = self.env["stock.picking"].browse([int(i) for i in picking_ids]).exists()
        if not pickings or not pickings.has_access("read"):
            return False
        unit = self.env.ref("uom.product_uom_unit", raise_if_not_found=False)
        missing = {}
        for move in pickings.move_ids.filtered(lambda m: m.state not in ("done", "cancel")):
            left = move.product_uom_qty - move.quantity
            if left > 1e-6:
                uom = self._uom(move)
                key = (move.product_id.display_name, "" if uom == unit else uom.name)
                missing[key] = missing.get(key, 0) + left
        # "20 Coils", "2.5 kg Steel"
        items = [{"label": " ".join(filter(None, [self._qty(q), u, p]))} for (p, u), q in missing.items()]
        return {"items": items[:6], "more": max(0, len(items) - 6), "outgoing": all(p.picking_type_code == "outgoing" for p in pickings)} if items else False

    @api.model
    def product_strip(self, model, res_id):
        """A storable product's stock in one strip: on hand, to deliver, incoming, forecast and the reordering minimum.
        False for other products or when the user may not read stock."""
        if "stock.quant" not in self.env or model not in ("product.template", "product.product"):
            return False
        product = self.env[model].browse(int(res_id)).exists()
        if not product or not product.has_access("read") or not product.is_storable:
            return False
        uom = product.uom_id.name
        on_hand, forecast = product.qty_available, product.virtual_available
        minimum = 0.0
        if "stock.warehouse.orderpoint" in self.env and self.env["stock.warehouse.orderpoint"].has_access("read"):
            variants = product.product_variant_ids if model == "product.template" else product
            minimum = sum(self.env["stock.warehouse.orderpoint"].search([("product_id", "in", variants.ids)]).mapped("product_min_qty"))
        chips = [
            {"key": "on_hand", "label": self.env._("On hand"), "value": self._qty(on_hand), "note": uom, "tone": "late" if on_hand < 0 else "plain"},
            {"key": "out", "label": self.env._("To deliver"), "value": self._qty(product.outgoing_qty), "note": uom, "tone": "plain"},
            {"key": "in", "label": self.env._("Incoming"), "value": self._qty(product.incoming_qty), "note": uom, "tone": "plain"},
            {"key": "forecast", "label": self.env._("Forecast"), "value": self._qty(forecast), "note": uom,
             "tone": "late" if forecast < 0 else ("warn" if minimum and forecast < minimum else "plain")},
        ]
        if minimum:
            chips.append({"key": "min", "label": self.env._("Minimum"), "value": self._qty(minimum), "note": uom, "tone": "plain"})
        can_make = self._can_make(product)
        if can_make is not None:
            chips.append({"key": "can_make", "label": self.env._("Can make"), "value": str(can_make), "note": self.env._("with the components in stock"),
                          "tone": "warn" if not can_make else "plain"})
        return chips

    # ------------------------------------------------------------------ manufacturing (when installed)
    @api.model
    def mo_steps(self, production_id):
        """A manufacturing order's routing as steps: each work order with its work centre and where it stands."""
        if "mrp.production" not in self.env:
            return False
        production = self.env["mrp.production"].browse(int(production_id)).exists()
        if not production or not production.has_access("read") or production.state in ("draft", "cancel"):
            return False
        workorders = production.workorder_ids.sorted(lambda w: (w.sequence if "sequence" in w._fields else 0, w.id))
        if not workorders:
            return False
        labels = dict(workorders._fields["state"]._description_selection(self.env))
        steps = [{"name": w.name, "where": w.workcenter_id.display_name, "state": w.state, "label": labels.get(w.state, w.state)}
                 for w in workorders]
        done = sum(1 for s in steps if s["state"] == "done")
        return {"steps": steps, "done": done, "total": len(steps)}

    def _can_make(self, product):
        """How many of a manufactured product the components in stock can make (first BoM level, storable
        components only); None when it has no bill of materials."""
        if "mrp.bom" not in self.env:
            return None
        variant = product.product_variant_id if product._name == "product.template" else product
        bom = self.env["mrp.bom"]._bom_find(variant, bom_type="normal").get(variant)
        if not bom:
            return None
        possible = []
        for line in bom.bom_line_ids:
            component = line.product_id
            if not component.is_storable or line.product_qty <= 0:
                continue
            line_uom = line.uom_id if "uom_id" in line._fields else line.product_uom_id   # 20: uom_id, 19: product_uom_id
            per_unit = line_uom._compute_quantity(line.product_qty, component.uom_id) / (bom.product_qty or 1.0)
            possible.append(int(max(component.qty_available, 0) // per_unit) if per_unit else 0)
        return min(possible) if possible else None
