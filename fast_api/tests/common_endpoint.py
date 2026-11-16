# Copyright 2021 Camptocamp SA
# @author: Simone Orsi <simone.orsi@camptocamp.com>
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

import contextlib

from odoo.tests.common import TransactionCase, tagged
from odoo.tools import DotDict

from odoo.addons.http_routing.tests.common import MockRequest


def routing_context(env):
    """Context needed to build ``ir.http.routing_map()`` while a request is active.

    Odoo 20: when ``website`` is installed it builds one routing map per host
    and reads ``host_id`` from the caller's context (a real request sets it
    before routing; MockRequest only sets it on the request's own env).
    """
    website = env.ref("base.default_website", raise_if_not_found=False)
    return {"host_id": website.id} if website else {}


@tagged("-at_install", "post_install")
class CommonEndpoint(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls._setup_env()
        cls._setup_records()
        cls.route_handler = cls.env["endpoint.route.handler"]

    @classmethod
    def _setup_env(cls):
        cls.env = cls.env(context=cls._setup_context())

    @classmethod
    def _setup_context(cls):
        return dict(
            cls.env.context,
            tracking_disable=True,
            **routing_context(cls.env),
        )

    @classmethod
    def _setup_records(cls):
        pass

    @contextlib.contextmanager
    def _get_mocked_request(
        self, env=None, httprequest=None, extra_headers=None, request_attrs=None
    ):
        registry = (env or self.env).registry
        original_init_modules = registry._init_modules
        with MockRequest(env or self.env) as mocked_request:
            mocked_request.httprequest = (
                DotDict(httprequest) if httprequest else mocked_request.httprequest
            )
            headers = {}
            headers.update(extra_headers or {})
            mocked_request.httprequest.headers = headers
            request_attrs = request_attrs or {}
            for k, v in request_attrs.items():
                setattr(mocked_request, k, v)
            mocked_request.make_response = lambda data, **kw: data
            mocked_request.registry._init_modules = set()
            try:
                yield mocked_request
            finally:
                # Restore the real _init_modules.
                # Without this, routing_map() keeps being built with an empty
                # module set and post_install HttpCase tests in other modules
                # get 404s.
                registry._init_modules = original_init_modules
