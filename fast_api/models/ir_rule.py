# Copyright 2026 Albatross
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

from odoo import api, models


class IrRule(models.Model):
    _inherit = "ir.rule"

    @api.model
    def _eval_context(self):
        """Let record rules refer to the partner authenticated by the API.

        ``authenticated_partner_env`` puts the partner id in the context;
        a rule domain can then use ``authenticated_partner_id``.
        """
        values = super()._eval_context()
        values["authenticated_partner_id"] = self.env.context.get(
            "authenticated_partner_id", False
        )
        return values

    def _compute_domain_keys(self):
        # Rule domains now depend on this context key, so it has to be part
        # of the cache key of _compute_domain.
        return [*super()._compute_domain_keys(), "authenticated_partner_id"]
