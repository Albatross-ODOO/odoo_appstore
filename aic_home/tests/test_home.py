# -*- coding: utf-8 -*-
import json
import re
from datetime import timedelta

from odoo import fields
from odoo.exceptions import AccessError, UserError
from odoo.tests import HttpCase, TransactionCase, new_test_user, tagged

ROLES = ("sales", "warehouse", "purchase", "accounts", "service", "owner")


@tagged("post_install", "-at_install")
class TestHomeData(TransactionCase):

    def _check_shape(self, data):
        for key in ("user", "summary", "missed", "today", "kpis", "panels", "app_order", "role_label"):
            self.assertIn(key, data)
        json.dumps(data, default=str)   # what the client receives must serialise
        for kpi in data["kpis"]:
            self.assertTrue(kpi["label"] and kpi["value"] is not None)
            if kpi["action"]:
                self.assertIn(kpi["action"]["res_model"], self.env)
        for panel in data["panels"]:
            for item in panel["items"]:
                self.assertTrue(self.env[item["model"]].browse(item["res_id"]).exists())

    def test_every_role_as_admin(self):
        admin = self.env.ref("base.user_admin")
        for role in ROLES:
            admin.aic_home_role = role
            data = self.env["aic.home"].with_user(admin).get_home_data()
            self.assertEqual(data["role"], role)
            self._check_shape(data)

    def test_every_role_as_plain_user(self):
        """A user with almost no rights still gets a working Home (blocks they cannot read are skipped)."""
        user = new_test_user(self.env, login="aic_plain", groups="base.group_user")
        for role in ROLES:
            user.aic_home_role = role
            self._check_shape(self.env["aic.home"].with_user(user).get_home_data())

    def test_totals_are_aggregates(self):
        """The KPI totals come from one aggregate query and match a sum over the records."""
        if "crm.lead" not in self.env:
            self.skipTest("crm is not installed")
        Lead = self.env["crm.lead"]
        domain = [("type", "=", "opportunity"), ("won_status", "=", "pending")]
        count, total = self.env["aic.home"]._count_sum(Lead, domain, "expected_revenue")
        leads = Lead.search(domain)
        self.assertEqual(count, len(leads))
        self.assertAlmostEqual(total, sum(leads.mapped("expected_revenue")), places=2)
        self.assertEqual(self.env["aic.home"]._count_sum(Lead, [("id", "=", 0)], "expected_revenue"), (0, 0.0))

    def test_compact_money(self):
        """Tiles show whole units below 10,000 and thousands / millions above (17,300 is 17.3K, not 1.7K)."""
        Home = self.env["aic.home"].with_context(lang="en_US")
        usd = self.env.ref("base.USD")
        usd.active = True
        self.assertEqual([Home._money_short(a, usd) for a in (4696.0, 10000, 17300, 69800, 2500000)],
                         ["$4,696", "$10K", "$17.3K", "$69.8K", "$2.5M"])
        self.assertEqual(Home._money_short(-2500, usd), "-$2,500")

    def test_customise_layout(self):
        """Hide and reorder blocks for the current role; Reset brings the role's layout back."""
        user = self.env.ref("base.user_admin")
        user.sudo().aic_home_layout = False
        user.aic_home_role = "sales"
        Home = self.env["aic.home"].with_user(user)
        data = Home.get_home_data()
        self.assertFalse(data["layout"]["custom"])
        self.assertTrue(all(data["sections"].values()))
        tiles = [t["key"] for t in data["layout"]["tiles"]]
        self.assertIn("kpi:overdue", tiles)
        order = list(reversed(tiles))
        data = Home.save_layout(hidden=["kpi:overdue", "today", "apps"], order=order)
        self.assertTrue(data["layout"]["custom"])
        self.assertNotIn("overdue", [k["key"] for k in data["kpis"]])
        self.assertEqual([t["key"] for t in data["layout"]["tiles"]], order, "the sheet lists hidden tiles too, in order")
        self.assertFalse(data["sections"]["today"] or data["sections"]["apps"])
        self.assertTrue(data["sections"]["missed"])
        # the choice belongs to the role: another role starts from its own layout
        user.aic_home_role = "warehouse"
        self.assertFalse(Home.get_home_data()["layout"]["custom"])
        user.aic_home_role = "sales"
        data = Home.reset_layout()
        self.assertFalse(data["layout"]["custom"])
        self.assertIn("overdue", [k["key"] for k in data["kpis"]])
        # junk is dropped, never stored
        data = Home.save_layout(hidden=[1, None, "x" * 500, "today", "today"], order=[{"a": 1}])
        self.assertEqual(user.sudo().aic_home_layout["sales"], {"hidden": ["today"], "order": []})

    def test_missed_and_reschedule(self):
        admin = self.env.ref("base.user_admin")
        partner = self.env["res.partner"].create({"name": "Core test partner"})
        activity = self.env["mail.activity"].create({
            "res_model_id": self.env["ir.model"]._get_id("res.partner"), "res_id": partner.id,
            "user_id": admin.id, "summary": "Core overdue call",
            "date_deadline": fields.Date.today() - timedelta(days=3),
        })
        data = self.env["aic.home"].with_user(admin).get_home_data()
        self.assertGreaterEqual(data["missed_count"], 1)
        moved = self.env["aic.home"].with_user(admin).reschedule_missed_to_today()
        self.assertGreaterEqual(moved, 1)
        self.assertEqual(activity.date_deadline, fields.Date.context_today(activity.with_user(admin)))

    def test_suggested_role_is_a_role(self):
        user = new_test_user(self.env, login="aic_suggest", groups="base.group_user")
        self.assertIn(user._aic_suggest_role(), ROLES)
        self.assertIn(self.env.ref("base.user_admin")._aic_suggest_role(), ROLES)


@tagged("post_install", "-at_install")
class TestBacklogCleanup(TransactionCase):

    def test_reschedule_and_rights(self):
        if "stock.picking" not in self.env:
            self.skipTest("Inventory is not installed")
        Picking = self.env["stock.picking"]
        late = Picking.search([("picking_type_code", "=", "outgoing"), ("state", "not in", ("done", "cancel", "draft"))], limit=2)
        if not late:
            self.skipTest("No open delivery in the demo data")
        late.write({"scheduled_date": fields.Datetime.now() - timedelta(days=90)})
        wizard = self.env["aic.backlog.cleanup"].create({"kind": "deliveries", "older_than_days": 30, "operation": "reschedule"})
        self.assertGreaterEqual(wizard.match_count, len(late))
        self.assertIn("records match", wizard.preview_html)
        plain = new_test_user(self.env, login="aic_noright", groups="base.group_user")
        with self.assertRaises(AccessError):
            wizard.with_user(plain).action_apply()
        wizard.confirm = True
        result = wizard.action_apply()
        self.assertEqual(result["tag"], "display_notification")
        self.assertTrue(all(p.scheduled_date.date() >= fields.Date.today() for p in late))


@tagged("post_install", "-at_install")
class TestStartScreen(HttpCase):

    def _session_info(self):
        page = self.url_open("/odoo").text
        match = re.search(r'"home_action_id":\s*(\d+|false|null)', page)
        self.assertTrue(match, "session_info not found in the web client page")
        return match.group(1)

    def test_home_is_the_start_screen(self):
        admin = self.env.ref("base.user_admin")
        admin.write({"password": "aic-test-password", "action_id": False})
        self.authenticate("admin", "aic-test-password")
        action = self.env.ref("aic_home.action_aic_home")
        self.assertEqual(self._session_info(), str(action.id))
        # a user's own home action wins
        own = self.env.ref("base.action_res_users")
        admin.write({"action_id": own.id})
        self.assertEqual(self._session_info(), str(own.id))
        # and the setting turns it off
        admin.action_id = False
        self.env["ir.config_parameter"].sudo().set_bool("aic_home.start_screen", False)
        self.assertNotEqual(self._session_info(), str(action.id))


@tagged("post_install", "-at_install")
class TestFocusQueue(TransactionCase):

    def setUp(self):
        super().setUp()
        self.user = new_test_user(self.env, login="aic_focus", groups="base.group_user,base.group_partner_manager")
        self.partner = self.env["res.partner"].create({"name": "Focus partner", "phone": "+91 98250 12345", "email": "f@example.com"})
        Activity = self.env["mail.activity"]
        model_id = self.env["ir.model"]._get_id("res.partner")
        today = fields.Date.today()
        self.old = Activity.create({"res_model_id": model_id, "res_id": self.partner.id, "user_id": self.user.id,
                                    "summary": "Old call", "date_deadline": today - timedelta(days=4)})
        self.new = Activity.create({"res_model_id": model_id, "res_id": self.partner.id, "user_id": self.user.id,
                                    "summary": "Today's email", "date_deadline": today})
        self.later = Activity.create({"res_model_id": model_id, "res_id": self.partner.id, "user_id": self.user.id,
                                      "summary": "Next week", "date_deadline": today + timedelta(days=7)})
        self.Focus = self.env["aic.focus"].with_user(self.user)

    def test_queue_order_and_card(self):
        queue = self.Focus.get_queue()
        self.assertEqual(queue["ids"][:2], [self.old.id, self.new.id], "oldest first, future activities excluded")
        self.assertNotIn(self.later.id, queue["ids"])
        self.assertEqual(queue["due"], 2)
        card = self.Focus.get_card(self.old.id)
        self.assertFalse(card["gone"])
        self.assertEqual(card["activity"]["late"], 4)
        self.assertEqual(card["contact"]["phone"], "+91 98250 12345")
        self.assertEqual(card["contact"]["tel"], "tel:+919825012345")
        self.assertEqual(card["contact"]["whatsapp"], "https://wa.me/919825012345")
        self.assertEqual(card["other_activities"], 2)

    def test_done_with_follow_up_and_snooze(self):
        counts = self.Focus.mark_done(self.old.id, "Spoke to them", 2)
        self.assertEqual(counts["done_today"], 1)
        self.assertFalse(self.old.active)
        follow = self.env["mail.activity"].search([("res_id", "=", self.partner.id), ("summary", "=", "Old call")])
        # "in 2 days" counts from the acting user's own today (their time zone), as the queue does
        self.assertEqual(follow.date_deadline, fields.Date.context_today(self.Focus) + timedelta(days=2))
        self.Focus.snooze(self.new.id, 1)
        self.assertGreater(self.new.date_deadline, fields.Date.today())
        self.assertTrue(self.Focus.get_card(self.old.id)["gone"])

    def test_follow_up_on_another_companys_record(self):
        """The queue lists every company's activities: done + follow-up on a record of a company that is not
        the active one in the browser must still work (it is refused by record rules otherwise)."""
        other_co = self.env["res.company"].create({"name": "Focus second company"})
        user = new_test_user(self.env, login="aic_focus_mc", groups="base.group_user,base.group_partner_manager",
                             company_id=self.env.company.id, company_ids=[(6, 0, [self.env.company.id, other_co.id])])
        partner = self.env["res.partner"].create({"name": "Second company partner", "company_id": other_co.id})
        act = self.env["mail.activity"].create({"res_model_id": self.env["ir.model"]._get_id("res.partner"), "res_id": partner.id,
                                                "user_id": user.id, "summary": "Cross-company call",
                                                "date_deadline": fields.Date.today() - timedelta(days=1)})
        focus = self.env["aic.focus"].with_user(user).with_context(allowed_company_ids=[self.env.company.id])
        focus.mark_done(act.id, "Done", 2)
        follow = self.env["mail.activity"].search([("res_id", "=", partner.id), ("summary", "=", "Cross-company call")])
        self.assertEqual(len(follow), 1)
        self.assertGreater(follow.date_deadline, fields.Date.today())

    def test_cannot_touch_someone_elses_activity(self):
        other = new_test_user(self.env, login="aic_focus_other", groups="base.group_user")
        with self.assertRaises(UserError):
            self.env["aic.focus"].with_user(other).mark_done(self.new.id)

    def test_home_offers_the_queue(self):
        data = self.env["aic.home"].with_user(self.user).get_home_data()
        self.assertEqual(data["queue"]["due"], 2)

    def test_todo_without_record(self):
        todo = self.env["mail.activity"].create({"user_id": self.user.id, "summary": "Personal to-do",
                                                 "date_deadline": fields.Date.today()})
        queue = self.Focus.get_queue()
        self.assertIn("__none__", [m["model"] for m in queue["models"]])
        self.assertEqual(self.Focus.get_queue("__none__")["ids"], [todo.id])
        card = self.Focus.get_card(todo.id)
        self.assertFalse(card["gone"])
        self.assertEqual(card["record"]["model"], False)


@tagged("post_install", "-at_install")
class TestProductionPanels(TransactionCase):
    """The warehouse role's manufacturing panels (when Manufacturing is installed)."""

    def test_late_production_on_home(self):
        if "mrp.production" not in self.env:
            self.skipTest("needs Manufacturing")
        storable = {"is_storable": True} if "is_storable" in self.env["product.product"]._fields else {"type": "product"}
        product = self.env["product.product"].create({"name": "Core Chair", **storable})
        component = self.env["product.product"].create({"name": "Core Seat", **storable})
        self.env["mrp.bom"].create({"product_tmpl_id": product.product_tmpl_id.id,
                                    "bom_line_ids": [(0, 0, {"product_id": component.id, "product_qty": 1})]})
        mo = self.env["mrp.production"].create({"product_id": product.id, "product_qty": 3,
                                                "date_start": fields.Datetime.now() - timedelta(days=3)})
        mo.action_confirm()
        admin = self.env.ref("base.user_admin")
        admin.aic_home_role = "warehouse"
        data = self.env["aic.home"].with_user(admin).get_home_data()
        panels = {p["key"]: p for p in data["panels"]}
        self.assertIn("mo_late", panels)
        self.assertGreaterEqual(int(panels["mo_late"]["badge"]), 1)
        self.assertIn("mo_short", panels, "no seat in stock: short of components")
        self.assertIn("mo_late", {k["key"] for k in data["kpis"]})


@tagged("post_install", "-at_install")
class TestHomeVisits(TransactionCase):
    """The service role's day: today's visits in visit order (when Project is installed)."""

    def test_visits_today(self):
        if "project.task" not in self.env:
            self.skipTest("needs Project")
        admin = self.env.ref("base.user_admin")
        admin.aic_home_role = "service"
        home = self.env["aic.home"].with_user(admin)
        bounds = home._aic_day_bounds(fields.Date.context_today(home))
        project = self.env["project.project"].create({"name": "Core Service"})
        customer = self.env["res.partner"].create({"name": "Core Site", "street": "12 Mill Road", "city": "Pune"})
        Task = self.env["project.task"]
        when = "planned_date_begin" if "planned_date_begin" in Task._fields else "date_deadline"
        vals = {"project_id": project.id, "partner_id": customer.id, "user_ids": [(6, 0, admin.ids)]}
        late = Task.create({**vals, "name": "Afternoon visit", when: bounds["day_start"] + timedelta(hours=15),
                            "date_deadline": bounds["day_start"] + timedelta(hours=17)})
        early = Task.create({**vals, "name": "Morning visit", when: bounds["day_start"] + timedelta(hours=9),
                             "date_deadline": bounds["day_start"] + timedelta(hours=11)})
        later = Task.create({**vals, "name": "Next week", when: bounds["week_end"], "date_deadline": bounds["week_end"] + timedelta(hours=2)})
        bare = Task.create({**vals, "name": "No customer", "partner_id": False, when: bounds["day_start"] + timedelta(hours=10),
                     "date_deadline": bounds["day_start"] + timedelta(hours=12)})
        panels = {p["key"]: p for p in home.get_home_data()["panels"]}
        self.assertIn("visits", panels)
        ids = [i["res_id"] for i in panels["visits"]["items"]]
        self.assertLess(ids.index(early.id), ids.index(late.id), "in visit order")
        self.assertNotIn(later.id, ids, "only today's")
        self.assertNotIn(bare.id, ids, "only at a customer's")
        item = panels["visits"]["items"][ids.index(early.id)]
        self.assertEqual(item["title"], "Core Site")
        self.assertIn("12 Mill Road, Pune", item["sub"])


@tagged("post_install", "-at_install")
class TestHomeOwnerMoney(TransactionCase):
    """The owner's money in and out: cash and bank, overdue receivables, bills due this week."""

    def test_owner_cash_and_bills(self):
        if "account.move" not in self.env or not self.env.company.chart_template:
            self.skipTest("needs Invoicing with a chart of accounts")
        admin = self.env.ref("base.user_admin")
        admin.aic_home_role = "owner"
        vendor = self.env["res.partner"].create({"name": "Core Supplies"})
        bill = self.env["account.move"].create({
            "move_type": "in_invoice", "partner_id": vendor.id, "invoice_date": fields.Date.today(),
            "invoice_date_due": fields.Date.today(),
            "invoice_line_ids": [(0, 0, {"name": "Compressor oil", "quantity": 1, "price_unit": 120.0, "tax_ids": [(6, 0, [])]})],
        })
        bill.action_post()
        data = self.env["aic.home"].with_user(admin).get_home_data()
        kpis = {k["key"]: k for k in data["kpis"]}
        journals = self.env["account.journal"].search([("type", "in", ("bank", "cash")), ("company_id", "in", self.env.companies.ids)])
        if journals.default_account_id:
            self.assertIn("cash", kpis)
            self.assertEqual(kpis["cash"]["action"]["xmlid"], "account.open_account_journal_dashboard_kanban")
        self.assertIn("bills_due", kpis)
        self.assertIn("bills_due", {p["key"] for p in data["panels"]})


@tagged("post_install", "-at_install")
class TestHomeSummaryWording(TransactionCase):
    """Counts of one read in the singular in the summary sentence."""

    def test_singular(self):
        base = {"missed_count": 0, "today": [], "kpis": [], "panels": [], "approvals_count": 0, "failed_count": 0}
        home = self.env["aic.home"]
        self.assertIn("1 message is waiting for you.", home._aic_summary(dict(base, for_you_count=1), "owner"))
        self.assertIn("2 messages are waiting for you.", home._aic_summary(dict(base, for_you_count=2), "owner"))
        purchase = dict(base, for_you_count=0, kpis=[{"key": "delayed", "value": "1"}])
        self.assertIn("1 receipt is late from its vendor.", home._aic_summary(purchase, "purchase"))
        one_today = dict(base, for_you_count=0, today=[{"title": "Call"}])
        self.assertIn("1 thing is on your list today.", home._aic_summary(one_today, "owner"))


@tagged("post_install", "-at_install")
class TestHomeUrl(HttpCase):
    """Home's URL segment must not be a client-action tag: Odoo's own ``home`` action sends the browser to ``/``."""

    def test_path_is_not_home(self):
        action = self.env.ref("aic_home.action_aic_home")
        self.assertEqual(action.path, "today")

    def test_old_home_links_redirect(self):
        self.authenticate("admin", "admin")
        for old, new in (("/odoo/home", "/odoo/today"), ("/odoo/home/42?debug=1", "/odoo/today/42?debug=1")):
            response = self.url_open(old, allow_redirects=False)
            self.assertEqual(response.status_code, 301, old)
            self.assertTrue(response.headers["Location"].endswith(new), response.headers["Location"])
        self.assertEqual(self.url_open("/odoo/today", allow_redirects=False).status_code, 200)
