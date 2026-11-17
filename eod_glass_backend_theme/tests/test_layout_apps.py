# -*- coding: utf-8 -*-
from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestLayoutApps(TransactionCase):
    """Customise home → Apps: a person's own app order and the apps they put away, per role."""

    def test_apps_saved_with_the_layout(self):
        Home = self.env["aic.home"].with_user(self.env.ref("base.user_admin"))
        data = Home.save_layout(hidden=["app:crm.crm_menu_root", "kpi:nothing"],
                                order=["app:sale.sale_menu_root", "app:contacts.menu_contacts"])
        self.assertEqual(data["layout"]["app_hidden"], ["crm.crm_menu_root"])
        self.assertEqual(data["layout"]["app_order"], ["sale.sale_menu_root", "contacts.menu_contacts"])
        # menus and access rights are untouched: the app is only listed under More apps
        menu = self.env.ref("base.menu_administration")
        self.assertTrue(menu.with_user(self.env.ref("base.user_admin"))._filter_visible_menus())
        data = Home.reset_layout()
        self.assertEqual(data["layout"]["app_hidden"], [])
        self.assertEqual(data["layout"]["app_order"], [])
