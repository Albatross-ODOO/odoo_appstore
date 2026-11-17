# -*- coding: utf-8 -*-
from odoo.tests import TransactionCase, new_test_user, tagged


@tagged("post_install", "-at_install")
class TestFailedSends(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = new_test_user(cls.env, login="aic_sender", groups="base.group_user,base.group_partner_manager")
        cls.other = new_test_user(cls.env, login="aic_other_sender", groups="base.group_user")
        cls.customer = cls.env["res.partner"].create({"name": "Failed Customer", "email": "nobody@example.invalid"})
        cls.doc = cls.env["res.partner"].create({"name": "Quote Document"})

    def _fail(self, author, record, model=None, res_id=None, failure="mail_smtp", status="exception"):
        message = self.env["mail.message"].create({
            "model": model or record._name, "res_id": res_id or record.id, "body": "Your quotation",
            "message_type": "comment", "author_id": author.partner_id.id,
        })
        mail = self.env["mail.mail"].sudo().create({"mail_message_id": message.id, "state": "exception",
                                                     "recipient_ids": [(4, self.customer.id)]})
        self.env["mail.notification"].sudo().create({
            "mail_message_id": message.id, "author_id": author.partner_id.id, "res_partner_id": self.customer.id,
            "notification_type": "email", "notification_status": status, "failure_type": failure,
            "mail_mail_id": mail.id,
        })
        return message, mail

    def _panel(self, user):
        data = self.env["aic.home"].with_user(user).get_home_data()
        return data, next((p for p in data["panels"] if p["key"] == "failed"), None)

    def test_own_failure_on_home(self):
        self._fail(self.user, self.doc)
        self._fail(self.user, self.doc, failure="mail_email_invalid")     # same document: one row, two sends
        data, panel = self._panel(self.user)
        self.assertTrue(panel, "a failed send shows the panel")
        self.assertEqual(data["panels"][0]["key"], "failed", "it comes first, for every role")
        self.assertEqual(panel["badge"], "1")
        item = panel["items"][0]
        self.assertEqual((item["model"], item["res_id"]), ("res.partner", self.doc.id))
        self.assertIn("Failed Customer", item["sub"])
        self.assertTrue(item["chip"], "two sends on one document")
        self.assertEqual([a["method"] for a in panel["actions"]], ["retry_failed_sends", "dismiss_failed_sends"])

    def test_not_others_and_not_unreadable(self):
        self._fail(self.other, self.doc)                                              # someone else's send
        self._fail(self.user, self.doc, model="ir.config_parameter",
                   res_id=self.env["ir.config_parameter"].sudo().search([], limit=1).id)   # a document the user cannot read
        _data, panel = self._panel(self.user)
        self.assertFalse(panel)

    def test_retry_queues_the_mail(self):
        _msg, mail = self._fail(self.user, self.doc)
        sentence = self.env["aic.home"].with_user(self.user).retry_failed_sends()
        self.assertEqual(mail.state, "outgoing")
        self.assertIn("1", sentence)
        self.assertEqual(mail.mail_message_id.notification_ids.notification_status, "ready")
        _data, panel = self._panel(self.user)
        self.assertFalse(panel, "a send on its way is not a failure")

    def test_retry_skips_bounces(self):
        _msg, mail = self._fail(self.user, self.doc, failure="mail_bounce", status="bounce")
        self.env["aic.home"].with_user(self.user).retry_failed_sends()
        self.assertEqual(mail.state, "exception", "a bounce is not retried: the address must be corrected")

    def test_dismiss(self):
        message, _mail = self._fail(self.user, self.doc)
        self.env["aic.home"].with_user(self.user).dismiss_failed_sends()
        self.assertEqual(message.notification_ids.notification_status, "canceled")
        _data, panel = self._panel(self.user)
        self.assertFalse(panel)

    def test_administrator_sees_the_company_list(self):
        self._fail(self.other, self.doc)                       # someone else's failed send
        admin = new_test_user(self.env, login="aic_failed_admin", groups="base.group_user,base.group_system")
        data, panel = self._panel(admin)
        self.assertTrue(panel, "an administrator gets the panel even with no failure of their own")
        self.assertFalse(panel["items"])
        self.assertIn("Everyone's failed sends", panel["footer"]["label"])
        action = panel["footer"]["action"]
        self.assertEqual(action["res_model"], "mail.message")
        self.assertIn(self._fail(self.other, self.doc)[0], self.env["mail.message"].search(action["domain"]))
        # a regular user never sees it
        _data, panel = self._panel(self.user)
        self.assertFalse(panel)
