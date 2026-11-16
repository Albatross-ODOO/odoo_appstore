# Copyright 2026 Albatross
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

from datetime import datetime, timedelta
from typing import Annotated

from odoo.api import Environment
from odoo.tests import new_test_user
from odoo.tools import mute_logger

from odoo.addons.base.models.res_partner import ResPartner
from odoo.addons.base.models.res_users import ResUsers

from fastapi import APIRouter, Depends, status

from ..dependencies import (
    api_key_user,
    api_key_user_env,
    authenticated_partner,
    authenticated_partner_from_api_key_user,
    authenticated_partner_impl,
)
from .common import FastAPITransactionCase

# Scope of the keys users create in Preferences > Security.
UI_KEY_SCOPE = "rpc"

router = APIRouter()


@router.get("/whoami")
def whoami(user: Annotated[ResUsers, Depends(api_key_user)]):
    return {"id": user.id}


@router.get("/env")
def env_info(env: Annotated[Environment, Depends(api_key_user_env)]):
    return {"uid": env.uid, "company_id": env.company.id}


@router.get("/settings")
def settings(env: Annotated[Environment, Depends(api_key_user_env)]):
    # System parameters are readable by administrators only.
    return env["ir.config_parameter"].search_count([])


@router.get("/partner")
def partner(partner: Annotated[ResPartner, Depends(authenticated_partner)]):
    return {"id": partner.id, "name": partner.name}


class TestApiKey(FastAPITransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env["fastapi.endpoint"]._load_demo_data()
        cls.default_fastapi_router = router
        cls.default_fastapi_running_user = cls.env.ref("fast_api.my_demo_app_user")
        cls.api_user = new_test_user(
            cls.env, login="fast_api_key_user", groups="base.group_user"
        )
        cls.key = cls._make_key(cls.api_user)

    @classmethod
    def _make_key(cls, user, scope=UI_KEY_SCOPE, expiration_date=None):
        return (
            cls.env["res.users.apikeys"]
            .with_user(user)
            .sudo()
            ._generate(scope, "fast_api test", expiration_date)
        )

    def _get(self, path, headers=None, **kwargs):
        with self._create_test_client(**kwargs) as client:
            return client.get(path, headers=headers or {})

    def test_bearer_header(self):
        response = self._get("/whoami", {"Authorization": f"Bearer {self.key}"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json(), {"id": self.api_user.id})

    def test_x_api_key_header(self):
        response = self._get("/whoami", {"X-API-Key": self.key})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json(), {"id": self.api_user.id})

    def _assert_refused(self, headers):
        response = self._get("/whoami", headers, raise_server_exceptions=False)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(response.json(), {"detail": "Invalid or missing API key"})

    @mute_logger("odoo.addons.fast_api.tests.common")
    def test_missing_key(self):
        self._assert_refused({})

    @mute_logger("odoo.addons.fast_api.tests.common")
    def test_wrong_key(self):
        self._assert_refused({"Authorization": f"Bearer {self.key[:-4]}0000"})
        self._assert_refused({"X-API-Key": "not-a-key"})
        # A key is not a password: Basic auth with it is refused too.
        self._assert_refused({"Authorization": f"Basic {self.key}"})

    @mute_logger("odoo.addons.fast_api.tests.common")
    def test_expired_key(self):
        expired = self._make_key(
            self.api_user, expiration_date=datetime.now() - timedelta(days=1)
        )
        self._assert_refused({"Authorization": f"Bearer {expired}"})

    @mute_logger("odoo.addons.fast_api.tests.common")
    def test_foreign_scope_key(self):
        other = self._make_key(self.api_user, scope="some_other_scope")
        self._assert_refused({"Authorization": f"Bearer {other}"})

    @mute_logger("odoo.addons.fast_api.tests.common")
    def test_archived_user(self):
        self.api_user.active = False
        self.env.flush_all()
        self._assert_refused({"Authorization": f"Bearer {self.key}"})

    def test_user_env(self):
        response = self._get("/env", {"Authorization": f"Bearer {self.key}"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.json(),
            {"uid": self.api_user.id, "company_id": self.api_user.company_id.id},
        )

    @mute_logger("odoo.addons.fast_api.tests.common")
    def test_user_env_applies_access_rights(self):
        response = self._get(
            "/settings",
            {"Authorization": f"Bearer {self.key}"},
            raise_server_exceptions=False,
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        admin_key = self._make_key(self.env.ref("base.user_admin"))
        response = self._get("/settings", {"Authorization": f"Bearer {admin_key}"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_authenticated_partner(self):
        response = self._get(
            "/partner",
            {"X-API-Key": self.key},
            dependency_overrides={
                authenticated_partner_impl: authenticated_partner_from_api_key_user
            },
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        partner = self.api_user.partner_id
        self.assertEqual(response.json(), {"id": partner.id, "name": partner.name})
