# -*- coding: utf-8 -*-
from datetime import timedelta

from odoo import fields
from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestPurchaseSummary(TransactionCase):
    """Purchase order in plain words: late lines and the Chase vendor e-mail."""

    def setUp(self):
        super().setUp()
        if "purchase.order" not in self.env:
            self.skipTest("needs Purchase")
        vendor = self.env["res.partner"].create({"name": "Core Vendor", "email": "vendor@example.com"})
        product = self.env["product.product"].create({"name": "Core Coil"})
        self.order = self.env["purchase.order"].create({
            "partner_id": vendor.id,
            "order_line": [(0, 0, {"product_id": product.id, "product_qty": 20, "price_unit": 5,
                                   "date_planned": fields.Datetime.now() - timedelta(days=3)})],
        })
        self.order.button_confirm()
        self.Summary = self.env["aic.purchase.summary"]

    def test_late_lines_and_chase(self):
        data = self.Summary.purchase_late(self.order.id)
        self.assertEqual(len(data["lines"]), 1)
        line = data["lines"][0]
        self.assertEqual((line["product"], line["left"], line["ordered"], line["days"]), ("Core Coil", "20", "20", 3))
        action = self.Summary.chase_vendor_action(self.order.id)
        self.assertEqual(action["res_model"], "mail.compose.message")
        self.assertEqual(action["context"]["default_res_ids"], self.order.ids)

    def test_nothing_on_drafts(self):
        self.order.button_cancel()
        self.assertFalse(self.Summary.purchase_late(self.order.id))
