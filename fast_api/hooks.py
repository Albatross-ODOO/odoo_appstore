# Copyright 2022 Camptocamp SA
# Copyright 2026 Albatross
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

import logging

from odoo.exceptions import UserError

from .registry import EndpointRegistry

_logger = logging.getLogger(__name__)

# The OCA modules this one is built from. They declare the same models
# (fastapi.endpoint, endpoint.route.*), so they cannot share a database
# with fast_api.
CONFLICTING_MODULES = ("fastapi", "endpoint_route_handler")


def _installed_conflicting_modules(cr):
    cr.execute(
        """
        SELECT name FROM ir_module_module
         WHERE name IN %s
           AND state IN ('installed', 'to install', 'to upgrade', 'to remove')
        """,
        [CONFLICTING_MODULES],
    )
    return sorted(row[0] for row in cr.fetchall())


def pre_init_hook(env):
    conflicting = _installed_conflicting_modules(env.cr)
    if conflicting:
        raise UserError(
            "FastAPI (fast_api) cannot be installed next to the OCA module(s) "
            f"{', '.join(conflicting)}: they define the same models. "
            "Uninstall them first, then install fast_api."
        )


def post_init_hook(env):
    _logger.info("Create the endpoint_route table")
    EndpointRegistry._setup_db(env.cr)


def uninstall_hook(env):
    # The route table, its sequence and triggers are created by hand in
    # post_init_hook, so the ORM does not know about them. Drop them, unless
    # an OCA endpoint_route_handler still uses the same table.
    if _installed_conflicting_modules(env.cr):
        return
    _logger.info("Drop the endpoint_route table")
    EndpointRegistry._teardown_db(env.cr)
