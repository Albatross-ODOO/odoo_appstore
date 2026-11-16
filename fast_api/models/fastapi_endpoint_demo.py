# Copyright 2022 ACSONE SA/NV
# Copyright 2026 Albatross (Odoo API key authentication)
# License LGPL-3.0 or later (http://www.gnu.org/licenses/LGPL).
from typing import Any

from odoo import api, fields, models
from odoo.exceptions import ValidationError

from fastapi import APIRouter

from ..dependencies import (
    authenticated_partner_from_api_key_user,
    authenticated_partner_from_basic_auth_user,
    authenticated_partner_impl,
)
from ..routers import demo_router, demo_router_doc


class FastapiEndpoint(models.Model):
    _inherit = "fastapi.endpoint"

    app: str = fields.Selection(
        selection_add=[("demo", "Demo Endpoint")], ondelete={"demo": "cascade"}
    )
    demo_auth_method = fields.Selection(
        selection=[("api_key", "Odoo API Key"), ("http_basic", "HTTP Basic")],
        string="Authentication method",
    )

    def _get_fastapi_routers(self) -> list[APIRouter]:
        if self.app == "demo":
            return [demo_router]
        return super()._get_fastapi_routers()

    @api.constrains("app", "demo_auth_method")
    def _valdiate_demo_auth_method(self):
        for rec in self:
            if rec.app == "demo" and not rec.demo_auth_method:
                raise ValidationError(
                    self.env._(
                        "The authentication method is required for app %(app)s",
                        app=rec.app,
                    )
                )

    @api.model
    def _fastapi_app_fields(self) -> list[str]:
        fields = super()._fastapi_app_fields()
        fields.append("demo_auth_method")
        return fields

    def _get_app(self):
        app = super()._get_app()
        if self.app == "demo":
            # Here we add the overrides to the authenticated_partner_impl method
            # according to the authentication method configured on the demo app
            if self.demo_auth_method == "http_basic":
                authenticated_partner_impl_override = (
                    authenticated_partner_from_basic_auth_user
                )
            else:
                authenticated_partner_impl_override = (
                    authenticated_partner_from_api_key_user
                )
            app.dependency_overrides[authenticated_partner_impl] = (
                authenticated_partner_impl_override
            )
        return app

    def _prepare_fastapi_app_params(self) -> dict[str, Any]:
        params = super()._prepare_fastapi_app_params()
        if self.app == "demo":
            tags_metadata = params.get("openapi_tags", []) or []
            tags_metadata.append({"name": "demo", "description": demo_router_doc})
            params["openapi_tags"] = tags_metadata
        return params

