# -*- coding: utf-8 -*-
from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestMrpSummary(TransactionCase):
    """Manufacturing in plain words: what a product can be made of now."""

    def setUp(self):
        super().setUp()
        if "mrp.bom" not in self.env:
            self.skipTest("needs Manufacturing")
        storable = {"is_storable": True} if "is_storable" in self.env["product.product"]._fields else {"type": "product"}
        self.table = self.env["product.product"].create({"name": "Core Table", **storable})
        self.leg = self.env["product.product"].create({"name": "Core Leg", **storable})
        self.top = self.env["product.product"].create({"name": "Core Top", **storable})
        self.env["mrp.bom"].create({
            "product_tmpl_id": self.table.product_tmpl_id.id, "product_qty": 1,
            "bom_line_ids": [(0, 0, {"product_id": self.leg.id, "product_qty": 4}),
                             (0, 0, {"product_id": self.top.id, "product_qty": 1})],
        })
        location = self.env["stock.warehouse"].search([("company_id", "=", self.env.company.id)], limit=1).lot_stock_id
        self.env["stock.quant"]._update_available_quantity(self.leg, location, 10)
        self.env["stock.quant"]._update_available_quantity(self.top, location, 5)
        self.Summary = self.env["aic.stock.summary"]

    def test_can_make(self):
        chips = {c["key"]: c for c in self.Summary.product_strip("product.product", self.table.id)}
        self.assertEqual(chips["can_make"]["value"], "2")       # 10 legs // 4 = 2, 5 tops
        self.assertNotIn("can_make", {c["key"] for c in self.Summary.product_strip("product.product", self.leg.id)})
