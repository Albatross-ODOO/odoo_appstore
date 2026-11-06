# -*- coding: utf-8 -*-
from odoo.tests import TransactionCase, new_test_user, tagged


@tagged("post_install", "-at_install")
class TestSwipeActions(TransactionCase):

    def setUp(self):
        super().setUp()
        self.Swipe = self.env["aic.swipe"]
        self.partner = self.env["res.partner"].create({"name": "Swipe Customer", "phone": "+1 555 010 2030"})

    def test_contact_keys(self):
        actions = self.Swipe.get_actions("res.partner", self.partner.id)
        self.assertEqual(actions["tel"], "tel:+15550102030")
        self.assertTrue(actions["whatsapp"] or actions["whatsapp_url"])
        self.assertTrue(actions["plan"])
        self.assertFalse(actions["primary"], "a contact has no next step")

    def test_unknown_or_missing_record(self):
        self.assertEqual(self.Swipe.get_actions("no.such.model", 1), {})
        self.assertEqual(self.Swipe.get_actions("res.partner", 0), {})
        self.assertEqual(self.Swipe.get_actions("res.partner", self.partner.id + 10 ** 6), {})

    def test_quotation_next_step(self):
        if "sale.order" not in self.env:
            self.skipTest("sale is not installed")
        order = self.env["sale.order"].create({"partner_id": self.partner.id})
        actions = self.Swipe.get_actions("sale.order", order.id)
        self.assertEqual(actions["primary"]["method"], "action_confirm")
        self.assertEqual(actions["tel"], "tel:+15550102030", "the customer's number")
        order.state = "sale"
        self.assertFalse(self.Swipe.get_actions("sale.order", order.id)["primary"], "confirmed: no Confirm key")

    def test_no_keys_without_read_access(self):
        if "sale.order" not in self.env:
            self.skipTest("sale is not installed")
        order = self.env["sale.order"].create({"partner_id": self.partner.id})
        outsider = new_test_user(self.env, login="swipe_outsider", groups="base.group_user")
        self.assertEqual(self.Swipe.with_user(outsider).get_actions("sale.order", order.id), {})
