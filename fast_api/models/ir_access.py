# Copyright 2026 Albatross
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

from odoo import models


class IrAccess(models.Model):
    _inherit = "ir.access"

    def _eval_context(self):
        """Let access domains refer to the partner authenticated by the API.

        ``authenticated_partner_env`` puts the partner id in the context;
        a domain can then use ``authenticated_partner_id``.
        """
        values = super()._eval_context()
        values["authenticated_partner_id"] = self.env.context.get(
            "authenticated_partner_id", False
        )
        return values

    def _get_access_context(self):
        # Access domains now depend on this context key, so it has to be part
        # of the cache key of the computed domains.
        yield from super()._get_access_context()
        yield self.env.context.get("authenticated_partner_id", False)
