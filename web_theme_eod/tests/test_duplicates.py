# -*- coding: utf-8 -*-
from odoo.tests import Form, TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestPartnerDuplicates(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        Partner = cls.env["res.partner"]
        cls.acme = Partner.create({"name": "Core Dup Acme", "is_company": True, "email": "info@aic-dup.example"})
        cls.jane = Partner.create({"name": "Jane Core", "parent_id": cls.acme.id, "email": "jane@aic-dup.example",
                                   "phone": "+32 470 12 34 56"})

    def test_same_email_or_phone(self):
        """A new contact with an existing e-mail (any case) or phone number names the existing contact."""
        form = Form(self.env["res.partner"])
        form.name = "Jane S."
        form.email = "JANE@aic-dup.example"
        self.assertIn(self.jane, form.aic_duplicate_ids)
        form.email = "someone.else@aic-dup.example"
        self.assertNotIn(self.jane, form.aic_duplicate_ids)
        form.phone = "+32 470 123 456"
        self.assertIn(self.jane, form.aic_duplicate_ids)

    def test_own_family_and_self_left_out(self):
        """A contact is not its own duplicate, nor are its company and the company's people."""
        self.assertFalse(self.jane.aic_duplicate_ids)
        colleague = self.env["res.partner"].create({"name": "Joe Core", "parent_id": self.acme.id,
                                                    "email": "jane@aic-dup.example"})
        self.assertFalse(colleague.aic_duplicate_ids)
        self.assertFalse(self.env["res.partner"].new({"name": "x", "email": "", "phone": "12"}).aic_duplicate_ids)


@tagged("post_install", "-at_install")
class TestCustomerOverview(TransactionCase):

    def test_overview_chips(self):
        """A company with an open quotation and an overdue unpaid invoice shows both (the invoice as late), from
        any of its contacts; a contact with nothing shows nothing."""
        Partner = self.env["res.partner"]
        company = Partner.create({"name": "Core Glance Co", "is_company": True})
        person = Partner.create({"name": "Glance Person", "parent_id": company.id})
        self.assertEqual(Partner.create({"name": "Nobody Glance"}).aic_customer_overview(), [])
        keys = set()
        if "sale.order" in self.env:
            product = self.env["product.product"].create({"name": "Glance item", "list_price": 100})
            self.env["sale.order"].create({"partner_id": person.id, "order_line": [(0, 0, {"product_id": product.id})]})
            keys.add("quotations")
        if "account.move" in self.env and self.env["account.journal"].search([("type", "=", "sale")], limit=1):
            inv = self.env["account.move"].create({
                "move_type": "out_invoice", "partner_id": company.id, "invoice_date": "2020-01-01",
                "invoice_date_due": "2020-01-31",
                "invoice_line_ids": [(0, 0, {"name": "Glance line", "quantity": 1, "price_unit": 50})]})
            inv.action_post()
            keys.add("invoices")
        chips = {c["key"]: c for c in person.aic_customer_overview()}
        self.assertTrue(keys <= set(chips), chips.keys())
        if "invoices" in keys:
            self.assertEqual(chips["invoices"]["tone"], "late")
