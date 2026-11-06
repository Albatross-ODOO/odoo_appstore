# -*- coding: utf-8 -*-
from markupsafe import Markup

from odoo.tests import TransactionCase, new_test_user, tagged


@tagged("post_install", "-at_install")
class TestLastCustomerMessage(TransactionCase):
    """Ticket form card: the customer's last public message, and whether the team answered since."""

    def setUp(self):
        super().setUp()
        if "helpdesk.ticket" not in self.env:
            self.skipTest("needs Helpdesk")
        self.company = self.env["res.partner"].create({"name": "Core Customer Co", "is_company": True})
        self.contact = self.env["res.partner"].create({"name": "Casey Customer", "parent_id": self.company.id})
        self.ticket = self.env["helpdesk.ticket"].create({"name": "Broken drawer", "partner_id": self.contact.id})
        company = self.ticket.company_id or self.env.company   # the default team may belong to another company
        self.agent = new_test_user(self.env, "aic_agent", groups="base.group_user,helpdesk.group_helpdesk_manager",
                                   company_id=company.id, company_ids=[(6, 0, company.ids)])
        self.Msg = self.env["mail.message"].with_user(self.agent)

    def _post(self, author, body, subtype="mail.mt_comment"):
        return self.ticket.message_post(body=Markup(body), author_id=author.id, message_type="comment", subtype_xmlid=subtype)

    def test_none(self):
        self.assertFalse(self.Msg.aic_last_customer_message("helpdesk.ticket", self.ticket.id))
        self.assertFalse(self.Msg.aic_last_customer_message("res.partner", self.contact.id))

    def test_last_and_answered(self):
        self._post(self.contact, "<p>First</p>")
        self._post(self.contact, "<p>The drawer <b>still</b> sticks</p>")
        self._post(self.agent.partner_id, "<p>internal</p>", subtype="mail.mt_note")
        data = self.Msg.aic_last_customer_message("helpdesk.ticket", self.ticket.id)
        self.assertEqual(data["text"], "The drawer still sticks")
        self.assertEqual(data["author"], self.contact.display_name)
        self.assertFalse(data["answered"])   # an internal note is not an answer
        self._post(self.agent.partner_id, "<p>On our way</p>")
        self.assertTrue(self.Msg.aic_last_customer_message("helpdesk.ticket", self.ticket.id)["answered"])

    def test_staff_is_not_the_customer(self):
        staff = new_test_user(self.env, "aic_staff", groups="base.group_user", company_id=self.agent.company_id.id,
                              company_ids=[(6, 0, self.agent.company_id.ids)])
        staff.partner_id.parent_id = self.company   # staff listed under the customer's company
        self._post(staff.partner_id, "<p>From staff</p>")
        self.assertFalse(self.Msg.aic_last_customer_message("helpdesk.ticket", self.ticket.id))
