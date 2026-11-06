# -*- coding: utf-8 -*-
from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestStockSummary(TransactionCase):
    """Inventory in plain words: what a transfer still misses, what a backorder would carry."""

    def setUp(self):
        super().setUp()
        if "stock.picking" not in self.env:
            self.skipTest("needs Inventory")
        self.product = self.env["product.product"].create({"name": "Core Coil", "is_storable": True} if "is_storable" in self.env["product.product"]._fields else {"name": "Core Coil", "type": "product"})
        warehouse = self.env["stock.warehouse"].search([("company_id", "=", self.env.company.id)], limit=1)
        self.picking = self.env["stock.picking"].create({
            "picking_type_id": warehouse.out_type_id.id,
            "location_id": warehouse.lot_stock_id.id,
            "location_dest_id": self.env.ref("stock.stock_location_customers").id,
            "move_ids": [(0, 0, {"product_id": self.product.id, "product_uom_qty": 20,
                                 "location_id": warehouse.lot_stock_id.id,
                                 "location_dest_id": self.env.ref("stock.stock_location_customers").id,
                                 **({"name": "Core Coil"} if "name" in self.env["stock.move"]._fields else {})})],
        })
        self.picking.action_confirm()
        self.Summary = self.env["aic.stock.summary"]

    def test_missing_on_a_waiting_delivery(self):
        rows = self.Summary.picking_missing(self.picking.id)
        self.assertEqual(len(rows), 1)
        self.assertEqual((rows[0]["product"], rows[0]["missing"], rows[0]["demand"]), ("Core Coil", "20", "20"))

    def test_backorder_sentence(self):
        data = self.Summary.backorder_summary(self.picking.ids)
        self.assertEqual(data["items"], [{"label": "20 Core Coil"}])
        self.assertTrue(data["outgoing"])

    def test_nothing_for_receipts_or_done(self):
        self.picking.action_cancel()
        self.assertFalse(self.Summary.picking_missing(self.picking.id))

    def test_product_strip(self):
        chips = {c["key"]: c for c in self.Summary.product_strip("product.product", self.product.id)}
        self.assertEqual(chips["on_hand"]["value"], "0")
        self.assertEqual(chips["out"]["value"], "20")
        self.assertEqual(chips["forecast"]["value"], "-20")
        self.assertEqual(chips["forecast"]["tone"], "late")
        service = self.env["product.product"].create({"name": "Core Service", "type": "service"})
        self.assertFalse(self.Summary.product_strip("product.product", service.id))
