# -*- coding: utf-8 -*-
from markupsafe import Markup

from odoo.tests import TransactionCase, new_test_user, tagged


@tagged("post_install", "-at_install")
class TestForYou(TransactionCase):
    """Home's "For you": unread mentions / inbox messages and unread chats."""

    def setUp(self):
        super().setUp()
        self.me = new_test_user(self.env, login="aic_foryou_me", groups="base.group_user", notification_type="inbox")
        self.colleague = new_test_user(self.env, login="aic_foryou_colleague", groups="base.group_user,base.group_partner_manager")
        self.doc = self.env["res.partner"].create({"name": "Mentioned Document"})

    def _panel(self):
        data = self.env["aic.home"].with_user(self.me).get_home_data()
        return data, next((p for p in data["panels"] if p["key"] == "foryou"), None)

    def test_nothing_waiting(self):
        data, panel = self._panel()
        self.assertFalse(panel)
        self.assertEqual(data["for_you_count"], 0)

    def test_mention_and_chat(self):
        self.doc.with_user(self.colleague).message_post(
            body=Markup("<p>Can you check this?</p>"), message_type="comment", subtype_xmlid="mail.mt_comment",
            partner_ids=self.me.partner_id.ids)
        chat = self.env["discuss.channel"].with_user(self.colleague)._get_or_create_chat(partners_to=self.me.partner_id.ids)
        chat.with_user(self.colleague).message_post(body=Markup("<p>Hi!</p>"), message_type="comment", subtype_xmlid="mail.mt_comment")
        data, panel = self._panel()
        self.assertTrue(panel)
        models = {(i["model"], i["res_id"]) for i in panel["items"]}
        self.assertIn(("res.partner", self.doc.id), models)
        self.assertIn(("discuss.channel", chat.id), models)
        self.assertEqual(data["for_you_count"], 2)
        self.assertIn("waiting for you", data["summary"])
