# Copyright 2021 Camptocamp SA
# @author: Simone Orsi <simone.orsi@camptocamp.com>
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).
from contextlib import contextmanager
from unittest.mock import patch

from odoo import api, modules
from odoo.tests import common
from odoo.tools import mute_logger

from ..registry import EndpointRegistry, invalidate_routing_cache
from .common_endpoint import CommonEndpoint, routing_context
from .fake_controllers import CTRLFake


@contextmanager
def new_rollbacked_env():
    # Borrowed from `component`
    registry = modules.registry.Registry(common.get_db_name())
    uid = api.SUPERUSER_ID
    cr = registry.cursor()
    try:
        env = api.Environment(cr, uid, {})
        yield env(context=routing_context(env))
    finally:
        cr.rollback()  # we shouldn't have to commit anything
        cr.close()


def make_new_route(env, **kw):
    model = env["endpoint.route.handler.tool"]
    vals = {
        "name": "Test custom route",
        "route": "/my/test/route",
        "request_method": "GET",
    }
    vals.update(kw)
    new_route = model.new(vals)
    return new_route


class TestEndpoint(CommonEndpoint):
    def tearDown(self):
        EndpointRegistry.wipe_registry_for(self.env.cr)
        super().tearDown()

    def test_routing_map_no_request(self):
        # Crons, `odoo shell` and core tests build the routing map with no
        # request bound. website's TestWebsiteTechnicalPage does, through
        # website.technical.page.get_static_routes(). No mocked request here
        # on purpose.
        invalidate_routing_cache(self.env)
        self.assertTrue(self.env["ir.http"].routing_map())

    def test_as_tool_base_data(self):
        new_route = make_new_route(self.env)
        self.assertEqual(new_route.route, "/my/test/route")
        first_hash = new_route.endpoint_hash
        self.assertTrue(first_hash)
        new_route.route += "/new"
        self.assertNotEqual(new_route.endpoint_hash, first_hash)

    def test_auth_type_routing_info(self):
        for auth_type in ("public", "user_endpoint", "bearer"):
            new_route = make_new_route(self.env, auth_type=auth_type)
            __, routing, __ = new_route._get_routing_info()
            self.assertEqual(routing["auth"], auth_type)

    def test_route_field_precomputed(self):
        """Regression guard: ensure ``precompute=True`` stays on ``route``.

        Without it, downstream modules that derive ``route`` via compute
        would hit a "Missing required value" error at INSERT time.
        """
        Model = type(self.env["endpoint.route.handler.tool"])

        def _fake_compute_route(self):
            for rec in self:
                rec.route = "/precompute/probe"

        with patch.object(Model, "_compute_route", _fake_compute_route):
            rec = self.env["endpoint.route.handler.tool"].create(
                {
                    "name": "Precompute test",
                    "request_method": "GET",
                }
            )
            self.assertEqual(rec.route, "/precompute/probe")

    @mute_logger("odoo.addons.base.models.ir_http")
    def test_as_tool_register_single_controller(self):
        new_route = make_new_route(self.env)
        options = {
            "handler": {
                "klass_dotted_path": CTRLFake._path,
                "method_name": "custom_handler",
            }
        }

        with self._get_mocked_request():
            new_route._register_single_controller(options=options, init=True)
            # Ensure the routing rule is registered
            rmap = self.env["ir.http"].routing_map()
            self.assertIn("/my/test/route", [x.rule for x in rmap._rules])

        # Ensure is updated when needed
        new_route.route += "/new"
        with self._get_mocked_request():
            new_route._register_single_controller(options=options, init=True)
            rmap = self.env["ir.http"].routing_map()
            self.assertNotIn("/my/test/route", [x.rule for x in rmap._rules])
            self.assertIn("/my/test/route/new", [x.rule for x in rmap._rules])

    @mute_logger("odoo.addons.base.models.ir_http")
    def test_as_tool_register_controllers(self):
        new_route = make_new_route(self.env)
        options = {
            "handler": {
                "klass_dotted_path": CTRLFake._path,
                "method_name": "custom_handler",
            }
        }

        with self._get_mocked_request():
            new_route._register_controllers(options=options, init=True)
            # Ensure the routing rule is registered
            rmap = self.env["ir.http"].routing_map()
            self.assertIn("/my/test/route", [x.rule for x in rmap._rules])

        # Ensure is updated when needed
        new_route.route += "/new"
        with self._get_mocked_request():
            new_route._register_controllers(options=options, init=True)
            rmap = self.env["ir.http"].routing_map()
            self.assertNotIn("/my/test/route", [x.rule for x in rmap._rules])
            self.assertIn("/my/test/route/new", [x.rule for x in rmap._rules])

    @mute_logger("odoo.addons.base.models.ir_http")
    def test_as_tool_register_controllers_dynamic_route(self):
        route = "/my/app/<model(app.model):foo>"
        new_route = make_new_route(self.env, route=route)
        options = {
            "handler": {
                "klass_dotted_path": CTRLFake._path,
                "method_name": "custom_handler",
            }
        }

        with self._get_mocked_request():
            new_route._register_controllers(options=options, init=True)
            # Ensure the routing rule is registered
            rmap = self.env["ir.http"].routing_map()
            self.assertIn(route, [x.rule for x in rmap._rules])


class TestEndpointCrossEnv(CommonEndpoint):
    def setUp(self):
        super().setUp()
        # DELETE rather than TRUNCATE: TRUNCATE locks the table until the end
        # of the test, and the second cursor below needs to read it.
        self.env.cr.execute("DELETE FROM endpoint_route")

    @mute_logger("odoo.addons.base.models.ir_http", "odoo.modules.registry")
    def test_cross_env_consistency(self):
        """Route updates reach the other transactions.

        Odoo 20 keeps one ormcache layer per transaction, and the second
        cursor only reads committed rows, so it cannot see the routes this
        test registers. What it must see at once is the new routing version
        (a sequence, outside transactions): that version is part of the
        routing map cache key, so the other worker rebuilds its map on its
        next request, from the committed routes.
        """
        options = {
            "handler": {
                "klass_dotted_path": CTRLFake._path,
                "method_name": "custom_handler",
            }
        }
        reg = EndpointRegistry.registry_for(self.env.cr)
        route = "/my/app/<model(app.model):foo>"
        make_new_route(self.env, route=route)._register_controllers(options=options)
        last_version0 = reg.last_version()

        with self._get_mocked_request():
            with new_rollbacked_env() as env2:
                rmap = self.env["ir.http"].routing_map()
                self.assertIn(route, [x.rule for x in rmap._rules])
                rmap2 = env2["ir.http"].routing_map()
                self.assertIs(env2["ir.http"].routing_map(), rmap2)
                for env in (self.env, env2):
                    self.assertEqual(
                        env["ir.http"]._endpoint_route_last_version(), last_version0
                    )

                route = "/my/new/<model(app.model):foo>"
                make_new_route(self.env, route=route)._register_controllers(
                    options=options
                )

                rmap = self.env["ir.http"].routing_map()
                self.assertIn(route, [x.rule for x in rmap._rules])
                for env in (self.env, env2):
                    self.assertGreater(
                        env["ir.http"]._endpoint_route_last_version(), last_version0
                    )
                # In production the commit signals the change and the next
                # request of the other worker starts with fresh caches:
                # simulate that for env2, which then rebuilds its map.
                env2.transaction.invalidate_ormcache("routing")
                self.assertIsNot(env2["ir.http"].routing_map(), rmap2)
