from odoo import fields, models

from fastapi import APIRouter

from ..routers import health_router, partner_router


class FastapiEndpoint(models.Model):
    _inherit = "fastapi.endpoint"

    # 1. Register the app: it becomes a choice of the endpoint's App field.
    app: str = fields.Selection(
        selection_add=[("starter", "Starter API")],
        ondelete={"starter": "cascade"},
    )

    # 2. Say which routers the app serves.
    def _get_fastapi_routers(self) -> list[APIRouter]:
        if self.app == "starter":
            return [health_router, partner_router]
        return super()._get_fastapi_routers()
