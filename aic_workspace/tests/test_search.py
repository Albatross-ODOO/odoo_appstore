# -*- coding: utf-8 -*-
from odoo.tests import TransactionCase, new_test_user, tagged


@tagged("post_install", "-at_install")
class TestRecordSearch(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Search = cls.env["aic.search"]
        cls.company = cls.env["res.partner"].create({"name": "Zyxwq Holdings", "is_company": True, "email": "hello@zyxwq.example"})
        cls.person = cls.env["res.partner"].create({"name": "Ann Zyxwq", "parent_id": cls.company.id})

    def test_contacts_found_with_kind_and_hint(self):
        results = self.Search.search_records("Zyxwq")
        by_id = {(r["model"], r["id"]): r for r in results}
        company = by_id[("res.partner", self.company.id)]
        self.assertEqual(company["kind"], "Company")
        self.assertIn("zyxwq.example", company["hint"])
        self.assertIn(("res.partner", self.person.id), by_id)

    def test_short_term_and_limit(self):
        self.assertEqual(self.Search.search_records("Z"), [])
        self.assertEqual(self.Search.search_records("  "), [])
        self.assertLessEqual(len(self.Search.search_records("a")), 12)

    def test_only_what_the_user_may_read(self):
        user = new_test_user(self.env, login="aic_search_plain", groups="base.group_user")
        results = self.Search.with_user(user).search_records("Zyxwq")
        self.assertTrue(results)
        for r in results:
            self.assertTrue(self.env[r["model"]].with_user(user).browse(r["id"]).has_access("read"))

    def test_invoices_only_documents(self):
        if "account.move" not in self.env:
            self.skipTest("Invoicing is not installed")
        for r in self.Search.search_records("MISC"):
            self.assertNotEqual(r["model"], "account.move", "journal entries are not offered, only invoices and bills")
