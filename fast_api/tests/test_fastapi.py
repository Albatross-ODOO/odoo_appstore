# Copyright 2022 ACSONE SA/NV
# License LGPL-3.0 or later (http://www.gnu.org/licenses/LGPL).

import base64
import os
import unittest
from contextlib import contextmanager

from odoo.tests.common import HttpCase, new_test_user, tagged
from odoo.tests.test_cursor import TestCursor
from odoo.tools import mute_logger

from fastapi import status

from ..schemas import DemoExceptionType
from .test_api_key import UI_KEY_SCOPE


@tagged("post_install", "-at_install")
@unittest.skipIf(os.getenv("SKIP_HTTP_CASE"), "EndpointHttpCase skipped")
class FastAPIHttpCase(HttpCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env["fastapi.endpoint"]._load_demo_data()
        cls.fastapi_demo_app = cls.env.ref("fast_api.fastapi_endpoint_demo")
        cls.fastapi_multi_demo_app = cls.env.ref(
            "fast_api.fastapi_endpoint_multislash_demo"
        )
        cls.fastapi_apps = cls.fastapi_demo_app + cls.fastapi_multi_demo_app
        cls.fastapi_apps._handle_registry_sync()
        lang = (
            cls.env["res.lang"]
            .with_context(active_test=False)
            .search([("code", "=", "fr_BE")])
        )
        lang.active = True

    @contextmanager
    def _mocked_commit(self):
        with unittest.mock.patch.object(
            TestCursor, "commit", return_value=None
        ) as mocked_commit:
            yield mocked_commit

    def _assert_expected_lang(self, accept_language, expected_lang):
        route = "/fastapi_demo/demo/lang"
        response = self.url_open(route, headers={"Accept-language": accept_language})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, expected_lang)

    def test_call(self):
        route = "/fastapi_demo/demo/"
        response = self.url_open(route)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, b'{"Hello":"World"}')

    def test_lang(self):
        self._assert_expected_lang("fr,en;q=0.7,en-GB;q=0.3", b'"fr_BE"')
        self._assert_expected_lang("en,fr;q=0.7,en-GB;q=0.3", b'"en_US"')
        self._assert_expected_lang("fr-FR,en;q=0.7,en-GB;q=0.3", b'"fr_BE"')
        self._assert_expected_lang("fr-FR;q=0.1,en;q=1.0,en-GB;q=0.8", b'"en_US"')

    def test_retrying(self):
        """Test that the retrying mechanism is working as expected with the
        FastAPI endpoints.
        """
        nbr_retries = 3
        route = f"/fastapi_demo/demo/retrying?nbr_retries={nbr_retries}"
        response = self.url_open(route, timeout=20)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(int(response.content), nbr_retries)

    def test_retrying_post(self):
        """Test that the retrying mechanism is working as expected with the
        FastAPI endpoints in case of POST request with a file.
        """
        nbr_retries = 3
        route = f"/fastapi_demo/demo/retrying?nbr_retries={nbr_retries}"
        response = self.url_open(
            route, timeout=20, files={"file": ("test.txt", b"test")}
        )
        self.assertEqual(response.status_code, 200)
        self.assertDictEqual(response.json(), {"retries": nbr_retries, "file": "test"})

    @mute_logger("odoo.http")
    def assert_exception_processed(
        self,
        exception_type: DemoExceptionType,
        error_message: str,
        expected_message: str,
        expected_status_code: int,
    ) -> None:
        with self._mocked_commit() as mocked_commit:
            route = (
                "/fastapi_demo/demo/exception?"
                f"exception_type={exception_type.value}&error_message={error_message}"
            )
            response = self.url_open(route, timeout=200)
            mocked_commit.assert_not_called()
            self.assertDictEqual(
                response.json(),
                {
                    "detail": expected_message,
                },
            )
            self.assertEqual(response.status_code, expected_status_code)

    def test_user_error(self) -> None:
        self.assert_exception_processed(
            exception_type=DemoExceptionType.user_error,
            error_message="test",
            expected_message="test",
            expected_status_code=status.HTTP_400_BAD_REQUEST,
        )

    def test_validation_error(self) -> None:
        self.assert_exception_processed(
            exception_type=DemoExceptionType.validation_error,
            error_message="test",
            expected_message="test",
            expected_status_code=status.HTTP_400_BAD_REQUEST,
        )

    def test_bare_exception(self) -> None:
        self.assert_exception_processed(
            exception_type=DemoExceptionType.bare_exception,
            error_message="test",
            expected_message="Internal Server Error",
            expected_status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    def test_access_error(self) -> None:
        self.assert_exception_processed(
            exception_type=DemoExceptionType.access_error,
            error_message="test",
            expected_message="test",
            expected_status_code=status.HTTP_403_FORBIDDEN,
        )

    def test_missing_error(self) -> None:
        self.assert_exception_processed(
            exception_type=DemoExceptionType.missing_error,
            error_message="test",
            expected_message="test",
            expected_status_code=status.HTTP_404_NOT_FOUND,
        )

    def test_http_exception(self) -> None:
        self.assert_exception_processed(
            exception_type=DemoExceptionType.http_exception,
            error_message="test",
            expected_message="test",
            expected_status_code=status.HTTP_409_CONFLICT,
        )

    @mute_logger("odoo.http")
    def test_request_validation_error(self) -> None:
        with self._mocked_commit() as mocked_commit:
            route = "/fastapi_demo/demo/exception?exception_type=BAD&error_message="
            response = self.url_open(route, timeout=200)
            mocked_commit.assert_not_called()
            self.assertEqual(response.status_code, 422)

    def test_client_errors_logged_without_traceback(self) -> None:
        """A 4xx raised by FastAPI is routine traffic: no ERROR in the log."""
        with self.assertLogs("odoo.http", level="INFO") as logs:
            for exception_type in ("HTTPException", "NOT_A_TYPE"):
                self.url_open(
                    "/fastapi_demo/demo/exception?"
                    f"exception_type={exception_type}&error_message=client"
                )
        self.assertTrue(logs.records)
        self.assertEqual({r.levelname for r in logs.records}, {"INFO"})
        self.assertFalse([r for r in logs.records if r.exc_info])

    def test_no_commit_on_exception(self) -> None:
        # this test check that the way we mock the cursor is working as expected
        # and that the transaction is rolled back in case of exception.
        with self._mocked_commit() as mocked_commit:
            url = "/fastapi_demo/demo"
            response = self.url_open(url, timeout=600)
            self.assertEqual(response.status_code, 200)
            mocked_commit.assert_called_once()

        self.assert_exception_processed(
            exception_type=DemoExceptionType.http_exception,
            error_message="test",
            expected_message="test",
            expected_status_code=status.HTTP_409_CONFLICT,
        )

    def test_url_matching(self):
        # Test the URL mathing method on the endpoint
        paths = ["/fastapi", "/fastapi_demo", "/fastapi/v1"]
        EndPoint = self.env["fastapi.endpoint"]
        self.assertEqual(
            EndPoint._find_first_matching_url_path(paths, "/fastapi_demo/test"),
            "/fastapi_demo",
        )
        self.assertEqual(
            EndPoint._find_first_matching_url_path(paths, "/fastapi/test"), "/fastapi"
        )
        self.assertEqual(
            EndPoint._find_first_matching_url_path(paths, "/fastapi/v2/test"),
            "/fastapi",
        )
        self.assertEqual(
            EndPoint._find_first_matching_url_path(paths, "/fastapi/v1/test"),
            "/fastapi/v1",
        )

    def test_multi_slash(self):
        route = "/fastapi/demo-multi/demo/"
        response = self.url_open(route, timeout=20)
        self.assertEqual(response.status_code, 200)
        self.assertIn(self.fastapi_multi_demo_app.root_path, str(response.url))

    def test_docs(self):
        for path in ("/fastapi_demo/docs", "/fastapi_demo/redoc"):
            response = self.url_open(path)
            self.assertEqual(response.status_code, 200, path)
        response = self.url_open("/fastapi_demo/openapi.json")
        self.assertEqual(response.status_code, 200)
        schema = response.json()
        self.assertEqual(schema["info"]["title"], self.fastapi_demo_app.name)
        self.assertIn("/demo/who_ami", schema["paths"])
        self.assertEqual(schema["servers"], [{"url": "/fastapi_demo"}])

    @staticmethod
    def _basic_auth(login, password):
        token = base64.b64encode(f"{login}:{password}".encode()).decode()
        return {"Authorization": f"Basic {token}"}

    @mute_logger("odoo.http")
    def test_basic_auth(self):
        user = new_test_user(
            self.env, login="fast_api_basic", password="fast_api_basic_pw"
        )
        route = "/fastapi_demo/demo/who_ami"
        response = self.url_open(
            route, headers=self._basic_auth("fast_api_basic", "fast_api_basic_pw")
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["name"], user.partner_id.name)
        response = self.url_open(
            route, headers=self._basic_auth("fast_api_basic", "wrong")
        )
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.headers.get("WWW-Authenticate"), "Basic")

    @mute_logger("odoo.http")
    def test_api_key_auth(self):
        user = new_test_user(self.env, login="fast_api_http_key")
        key = (
            self.env["res.users.apikeys"]
            .with_user(user)
            .sudo()
            ._generate(UI_KEY_SCOPE, "http test", None)
        )
        # A dedicated endpoint: the shared demo apps stay pooled with their
        # own auth method for the other tests.
        endpoint = self.env["fastapi.endpoint"].create(
            {
                "name": "API key demo",
                "app": "demo",
                "demo_auth_method": "api_key",
                "root_path": "/fastapi_api_key_demo",
                "user_id": self.env.ref("fast_api.my_demo_app_user").id,
            }
        )
        endpoint._handle_registry_sync()
        route = "/fastapi_api_key_demo/demo/who_ami"
        for headers in ({"Authorization": f"Bearer {key}"}, {"X-API-Key": key}):
            response = self.url_open(route, headers=headers)
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json()["name"], user.partner_id.name)
        for headers in ({"X-API-Key": "wrong"}, {}):
            response = self.url_open(route, headers=headers)
            self.assertEqual(response.status_code, 401)
            self.assertEqual(response.headers.get("WWW-Authenticate"), "Bearer")

    def test_sync_and_archive(self):
        endpoint = self.env["fastapi.endpoint"].create(
            {
                "name": "Not synced yet",
                "app": "demo",
                "demo_auth_method": "http_basic",
                "root_path": "/fastapi_not_synced",
                "user_id": self.env.ref("fast_api.my_demo_app_user").id,
            }
        )
        self.assertFalse(endpoint.registry_sync)
        self.assertEqual(self.url_open("/fastapi_not_synced/demo").status_code, 404)
        endpoint._handle_registry_sync()
        self.assertEqual(self.url_open("/fastapi_not_synced/demo").status_code, 200)
        endpoint.active = False
        self.assertFalse(endpoint.registry_sync)
        endpoint._handle_registry_sync()
        self.assertEqual(self.url_open("/fastapi_not_synced/demo").status_code, 404)
