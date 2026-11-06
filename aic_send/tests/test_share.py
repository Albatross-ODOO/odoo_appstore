# -*- coding: utf-8 -*-
import re

from odoo.exceptions import UserError
from odoo.tests import HttpCase, TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestWhatsappShare(TransactionCase):

    def setUp(self):
        super().setUp()
        self.partner = self.env["res.partner"].create({
            "name": "Asha Mehta", "phone": "098250 12345", "email": "asha@example.com",
            "country_id": self.env.ref("base.in").id,
        })

    def _wizard(self, record):
        return self.env["aic.whatsapp.share"].with_context(
            default_res_model=record._name, default_res_id=record.id).create({})

    def test_contact(self):
        wizard = self._wizard(self.partner)
        self.assertEqual(re.sub(r"\D", "", wizard.phone), "919825012345")
        self.assertIn("Hello Asha Mehta,", wizard.message)
        self.assertFalse(wizard.link, "a contact has no customer portal page")
        result = wizard.action_open_whatsapp()
        self.assertEqual(result["type"], "ir.actions.act_url")
        self.assertTrue(result["url"].startswith("https://wa.me/919825012345?text=Hello%20Asha%20Mehta"))
        note = self.partner.message_ids[:1]
        self.assertIn("Shared on WhatsApp", note.body)

    def test_quotation(self):
        if "sale.order" not in self.env:
            self.skipTest("Sales is not installed")
        product = self.env["product.product"].create({"name": "Core test product", "list_price": 1000})
        order = self.env["sale.order"].create({
            "partner_id": self.partner.id,
            "order_line": [(0, 0, {"product_id": product.id, "product_uom_qty": 2})],
        })
        wizard = self._wizard(order)
        self.assertIn(order.name, wizard.message)
        self.assertTrue(wizard.link and "access_token" in wizard.link, wizard.link)
        self.assertIn(wizard.link, wizard.message)
        wizard.action_open_whatsapp()
        self.assertEqual(order.state, "sent", "sharing a draft quotation marks it as sent")

    def test_company_greeting(self):
        company = self.env["res.partner"].create({"name": "Ready Mat", "phone": "+1 803 873 6126"})
        self.assertIn("Hello Ready Mat,", self._wizard(company).message)
        person = self.env["res.partner"].create({"name": "Joel Willis", "parent_id": company.id, "phone": "+1 803 873 6127"})
        self.assertIn("Hello Joel,", self._wizard(person).message)
        self.assertTrue(self._wizard(company).action_open_whatsapp()["close"])

    def test_number_required(self):
        wizard = self._wizard(self.partner)
        wizard.phone = "12"
        with self.assertRaises(UserError):
            wizard.action_open_whatsapp()


@tagged("post_install", "-at_install")
class TestShareSetting(HttpCase):

    def test_flag_in_session(self):
        admin = self.env.ref("base.user_admin")
        admin.password = "aic-test-password"
        self.authenticate("admin", "aic-test-password")
        self.assertIn('"aic_whatsapp_share": true', self.url_open("/odoo").text)
        self.env["ir.config_parameter"].sudo().set_param("aic_send.whatsapp_share", "False")
        self.assertIn('"aic_whatsapp_share": false', self.url_open("/odoo").text)
