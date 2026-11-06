# -*- coding: utf-8 -*-
from odoo.exceptions import UserError
from odoo.tests import TransactionCase, new_test_user, tagged


@tagged("post_install", "-at_install")
class TestApprovals(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        if "purchase.order" not in cls.env:
            return
        cls.manager = new_test_user(cls.env, login="aic_po_manager",
                                    groups="base.group_user,purchase.group_purchase_manager")
        cls.buyer = new_test_user(cls.env, login="aic_po_buyer", groups="base.group_user,purchase.group_purchase_user")
        vendor = cls.env["res.partner"].create({"name": "Core Approval Vendor"})
        product = cls.env["product.product"].create({"name": "Core Approval Item", "standard_price": 10})
        cls.po = cls.env["purchase.order"].create({
            "partner_id": vendor.id,
            "order_line": [(0, 0, {"product_id": product.id, "product_qty": 3, "price_unit": 1000})],
        })
        cls.po.write({"state": "to approve"})

    def _panel(self, user):
        data = self.env["aic.home"].with_user(user).get_home_data()
        return data, next((p for p in data["panels"] if p["key"] == "approvals"), None)

    def test_manager_sees_and_approves(self):
        if "purchase.order" not in self.env:
            self.skipTest("Purchase is not installed")
        data, panel = self._panel(self.manager)
        self.assertTrue(panel, "a purchase order to approve shows the panel")
        self.assertIn(("purchase.order", self.po.id), [(i["model"], i["res_id"]) for i in panel["items"]])
        self.assertTrue(all(i.get("approve") for i in panel["items"]))
        self.assertEqual(data["kpis"][0]["key"], "approvals")
        self.env["aic.home"].with_user(self.manager).approve_item("purchase.order", self.po.id)
        self.assertEqual(self.po.state, "purchase")
        _data, panel = self._panel(self.manager)
        self.assertFalse(panel and any(i["res_id"] == self.po.id for i in panel["items"]))

    def test_buyer_does_not_approve(self):
        if "purchase.order" not in self.env:
            self.skipTest("Purchase is not installed")
        _data, panel = self._panel(self.buyer)
        self.assertFalse(panel)
        with self.assertRaises(UserError):
            self.env["aic.home"].with_user(self.buyer).approve_item("purchase.order", self.po.id)
        self.assertEqual(self.po.state, "to approve")


@tagged("post_install", "-at_install")
class TestExpenseApprovals(TransactionCase):

    def test_submitted_expense_to_its_approver(self):
        """An expense submitted to me appears in To approve and Approve approves it (Odoo 19/20: per expense)."""
        if "hr.expense" not in self.env or "hr.expense.sheet" in self.env:
            self.skipTest("Expenses (per-expense approval) are not installed")
        manager = new_test_user(self.env, login="aic_exp_manager",
                                groups="base.group_user,hr_expense.group_hr_expense_team_approver")
        employee = self.env["hr.employee"].create({"name": "Core Spender", "expense_manager_id": manager.id})
        product = self.env["product.product"].search([("can_be_expensed", "=", True)], limit=1)
        expense = self.env["hr.expense"].create({"name": "Taxi", "employee_id": employee.id,
                                                 "product_id": product.id, "total_amount_currency": 42})
        expense.action_submit()
        self.assertEqual((expense.state, expense.manager_id), ("submitted", manager))
        data = self.env["aic.home"].with_user(manager).get_home_data()
        panel = next((p for p in data["panels"] if p["key"] == "approvals"), None)
        self.assertTrue(panel and ("hr.expense", expense.id) in [(i["model"], i["res_id"]) for i in panel["items"]])
        self.env["aic.home"].with_user(manager).approve_item("hr.expense", expense.id)
        self.assertEqual(expense.state, "approved")


@tagged("post_install", "-at_install")
class TestRefuse(TransactionCase):

    def test_refuse_purchase_order_with_reason(self):
        """Refuse needs a reason, cancels the order and posts the reason; a buyer cannot refuse."""
        if "purchase.order" not in self.env:
            self.skipTest("Purchase is not installed")
        manager = new_test_user(self.env, login="aic_ref_manager", groups="base.group_user,purchase.group_purchase_manager")
        buyer = new_test_user(self.env, login="aic_ref_buyer", groups="base.group_user,purchase.group_purchase_user")
        vendor = self.env["res.partner"].create({"name": "Core Refuse Vendor"})
        product = self.env["product.product"].create({"name": "Core Refuse Item", "standard_price": 10})
        po = self.env["purchase.order"].create({"partner_id": vendor.id,
                                                "order_line": [(0, 0, {"product_id": product.id, "product_qty": 1, "price_unit": 900})]})
        po.write({"state": "to approve"})
        Home = self.env["aic.home"]
        with self.assertRaises(UserError):
            Home.with_user(manager).refuse_item("purchase.order", po.id, "  ")
        with self.assertRaises(UserError):
            Home.with_user(buyer).refuse_item("purchase.order", po.id, "Too expensive")
        self.assertEqual(po.state, "to approve")
        Home.with_user(manager).refuse_item("purchase.order", po.id, "Too expensive")
        self.assertEqual(po.state, "cancel")
        self.assertIn("Too expensive", po.message_ids[0].body)

    def test_refuse_expense_with_reason(self):
        if "hr.expense" not in self.env or "hr.expense.sheet" in self.env:
            self.skipTest("Expenses (per-expense approval) are not installed")
        manager = new_test_user(self.env, login="aic_exp_ref_manager",
                                groups="base.group_user,hr_expense.group_hr_expense_team_approver")
        employee = self.env["hr.employee"].create({"name": "Core Refused Spender", "expense_manager_id": manager.id})
        product = self.env["product.product"].search([("can_be_expensed", "=", True)], limit=1)
        expense = self.env["hr.expense"].create({"name": "Dinner", "employee_id": employee.id,
                                                 "product_id": product.id, "total_amount_currency": 80})
        expense.action_submit()
        self.env["aic.home"].with_user(manager).refuse_item("hr.expense", expense.id, "No receipt")
        self.assertEqual(expense.state, "refused")
