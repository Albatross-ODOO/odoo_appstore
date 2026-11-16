from odoo.tests import new_test_user, tagged

from odoo.addons.fast_api.tests.common import FastAPITransactionCase

from fastapi import status

from ..routers import health_router, partner_router

# Scope of the keys users create in Preferences > Security.
UI_KEY_SCOPE = "rpc"


@tagged("post_install", "-at_install")
class TestStarterApi(FastAPITransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.default_fastapi_running_user = cls.env.ref("starter_api.user_starter_api")
        # Creating contacts needs the "Contact Creation" right: the API runs
        # with the key owner's access rights, like the web client.
        cls.user = new_test_user(
            cls.env,
            login="starter_api_tester",
            groups="base.group_user,base.group_partner_manager",
        )
        cls.key = (
            cls.env["res.users.apikeys"]
            .with_user(cls.user)
            .sudo()
            ._generate(UI_KEY_SCOPE, "starter test", None)
        )
        cls.headers = {"Authorization": f"Bearer {cls.key}"}

    def test_health_is_public(self):
        with self._create_test_client(router=health_router) as client:
            response = client.get("/health")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json(), {"status": "ok"})

    def test_key_required(self):
        with self._create_test_client(
            router=partner_router, raise_server_exceptions=False
        ) as client:
            response = client.get("/me")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_me(self):
        with self._create_test_client(router=partner_router) as client:
            response = client.get("/me", headers=self.headers)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["login"], "starter_api_tester")

    def test_create_read_search(self):
        with self._create_test_client(router=partner_router) as client:
            response = client.post(
                "/partners",
                headers=self.headers,
                json={"name": "Starter Test Contact", "email": "starter@example.com"},
            )
            self.assertEqual(response.status_code, status.HTTP_201_CREATED)
            created = response.json()
            self.assertEqual(created["email"], "starter@example.com")
            self.assertIsNone(created["phone"])

            response = client.get(f"/partners/{created['id']}", headers=self.headers)
            self.assertEqual(response.json()["name"], "Starter Test Contact")

            response = client.get(
                "/partners",
                headers=self.headers,
                params={"search": "Starter Test", "page_size": 5},
            )
            body = response.json()
            self.assertEqual(body["count"], 1)
            self.assertEqual(body["items"][0]["id"], created["id"])

    def test_access_rights_apply(self):
        reader = new_test_user(self.env, login="starter_api_reader")
        key = (
            self.env["res.users.apikeys"]
            .with_user(reader)
            .sudo()
            ._generate(UI_KEY_SCOPE, "reader", None)
        )
        with self._create_test_client(
            router=partner_router, raise_server_exceptions=False
        ) as client:
            response = client.post(
                "/partners",
                headers={"X-API-Key": key},
                json={"name": "Not allowed"},
            )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_errors(self):
        with self._create_test_client(
            router=partner_router, raise_server_exceptions=False
        ) as client:
            response = client.get("/partners/999999999", headers=self.headers)
            self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
            response = client.post("/partners", headers=self.headers, json={"name": ""})
            self.assertEqual(response.status_code, 422)
