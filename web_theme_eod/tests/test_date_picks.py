# -*- coding: utf-8 -*-
from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestDatePicks(TransactionCase):

    def test_quick_dates_in_both_activity_forms(self):
        """Schedule Activity and the activity form carry the quick due dates right after the due date."""
        for model, ref in (("mail.activity.schedule", "mail.mail_activity_schedule_view_form"),
                           ("mail.activity", "mail.mail_activity_view_form_popup")):
            arch = self.env[model].get_view(self.env.ref(ref).id, "form")["arch"]
            self.assertIn('name="aic_date_picks"', arch, model)
            self.assertLess(arch.index('name="date_deadline"'), arch.index('name="aic_date_picks"'), model)
