# Copyright 2026 Albatross
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

from odoo.exceptions import UserError
from odoo.tests.common import TransactionCase, tagged
from odoo.tools import sql

from ..hooks import pre_init_hook
from ..registry import EndpointRegistry
from .fake_controllers import CTRLFake


@tagged("-at_install", "post_install")
class TestHooks(TransactionCase):
    def _set_module_state(self, name, state):
        module = self.env["ir.module.module"].search([("name", "=", name)])
        if module:
            module.state = state
        else:
            self.env["ir.module.module"].create({"name": name, "state": state})
        # The hook reads the states with SQL.
        self.env.flush_all()

    def test_pre_init_hook_accepts_clean_database(self):
        for name in ("fastapi", "endpoint_route_handler"):
            self._set_module_state(name, "uninstalled")
        pre_init_hook(self.env)

    def test_pre_init_hook_refuses_oca_modules(self):
        for name in ("fastapi", "endpoint_route_handler"):
            self._set_module_state(name, "uninstalled")
        for name in ("fastapi", "endpoint_route_handler"):
            self._set_module_state(name, "installed")
            with self.assertRaisesRegex(UserError, name):
                pre_init_hook(self.env)
            self._set_module_state(name, "uninstalled")

    def test_teardown_and_setup_db(self):
        cr = self.env.cr
        EndpointRegistry._teardown_db(cr)
        self.assertFalse(sql.table_exists(cr, "endpoint_route"))
        cr.execute("SELECT 1 FROM pg_class WHERE relname = 'endpoint_route_version'")
        self.assertFalse(cr.fetchone())
        # Unregistering routes once the table is gone must not fail: the
        # uninstall hook runs before the module's records are deleted.
        self.assertFalse(EndpointRegistry.registry_for(cr).drop_rules(("a:1",)))

        # A reinstall rebuilds everything, version tracking included.
        EndpointRegistry._setup_db(cr)
        self.assertTrue(sql.table_exists(cr, "endpoint_route"))
        reg = EndpointRegistry.registry_for(cr)
        options = {
            "handler": {
                "klass_dotted_path": CTRLFake._path,
                "method_name": "handler1",
            }
        }
        versions = []
        for i in (1, 2):
            route = f"/hooks/test{i}"
            rule = reg.make_rule(
                f"hooks:{i}", route, options, {"routes": [route]}, f"h{i}"
            )
            reg.update_rules([rule])
            versions.append(reg.last_version())
        self.assertGreater(versions[1], versions[0])
        self.assertEqual(
            sorted(r.key for r in reg.get_rules(keys=("hooks:1", "hooks:2"))),
            ["hooks:1", "hooks:2"],
        )
