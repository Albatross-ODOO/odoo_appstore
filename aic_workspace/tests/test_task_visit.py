# -*- coding: utf-8 -*-
from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestTaskVisit(TransactionCase):
    """A task as a visit: who, where, call, deadline, sub-tasks."""

    def test_visit(self):
        if "project.task" not in self.env:
            self.skipTest("needs Project")
        customer = self.env["res.partner"].create({"name": "Core Site", "street": "12 Mill Road", "city": "Pune", "zip": "411001",
                                                   "phone": "+91 98250 12345"})
        project = self.env["project.project"].create({"name": "Core Service"})
        task = self.env["project.task"].create({"name": "Fix the compressor", "project_id": project.id, "partner_id": customer.id})
        self.env["project.task"].create({"name": "Check pressure", "project_id": project.id, "parent_id": task.id})
        visit = self.env["aic.project.summary"].task_visit(task.id)
        self.assertEqual(visit["customer"], "Core Site")
        self.assertIn("12 Mill Road", visit["address"])
        self.assertEqual(visit["tel"], "tel:+919825012345")
        self.assertTrue(visit["map"].startswith("https://www.google.com/maps/search/?api=1&query="))
        self.assertEqual((visit["subtasks"], visit["subtasks_done"]), (1, 0))
        task.partner_id = False
        self.assertFalse(self.env["aic.project.summary"].task_visit(task.id))
