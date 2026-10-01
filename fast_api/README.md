# FastAPI - REST API Framework for Odoo 18

`fast_api` lets an Odoo server publish REST APIs written with
[FastAPI](https://fastapi.tiangolo.com/). Each API is served by Odoo itself, on
the same port, with the same users, access rights and database transaction as
the web client, and documents itself with Swagger UI, ReDoc and an OpenAPI
schema.

- One module, no other Odoo dependency than `base` and `web`
- Community and Enterprise
- Authentication ready to use: **Odoo API keys** (`Authorization: Bearer` or
  `X-API-Key`) and **HTTP Basic**, or plug in your own (JWT, OAuth, ...)
- Odoo exceptions become JSON errors with the right HTTP status
- A starter template and a test helper to write your own API in minutes

---

## 1. Installation

### 1.1 Python packages

Install these packages in the Python environment that runs Odoo:

```bash
pip install "fastapi>=0.110" "pydantic>=2" python-multipart ujson "a2wsgi>=1.10.6" parse-accept-language
```

The module refuses to install until they are present (Odoo shows
*External dependency ... not installed*).

**Odoo.sh**: add the same lines to the `requirements.txt` file at the root of
your repository and push; Odoo.sh installs them on the next build.

```text
fastapi>=0.110
pydantic>=2
python-multipart
ujson
a2wsgi>=1.10.6
parse-accept-language
```

Versions this release was tested with: fastapi 0.141.1, starlette 1.6.0,
pydantic 2.13.4, a2wsgi 1.10.10, python-multipart 0.0.32, ujson 5.13.0,
parse-accept-language 0.1.2, Python 3.12.

### 1.2 The module

1. Copy the `fast_api` folder into a folder of your addons path.
2. Restart Odoo.
3. *Apps > Update Apps List*, search **FastAPI**, click **Install**.

A **FastAPI** app appears in the main menu. Administrators get the
*FastAPI / Administrator* role at install; give *FastAPI / User* to people who
should only see the endpoints.

### 1.3 Servers hosting several databases

An API call must be routed to a database before FastAPI runs. Odoo tries, in
this order: the session cookie, the only database left by `--db-filter`, then
the `?db=<name>` query parameter (added by this module, also read from the
`Referer` of the Swagger page).

On a multi-database server, have your API clients add `?db=<name>` to their
calls, and load the module server-wide so `?db=` works from the first request
of each worker:

```ini
; odoo.conf
server_wide_modules = base,web,fast_api
```

A server with a single database, or with `dbfilter = ^%d$`, needs none of this.

---

## 2. Try it in five minutes

### 2.1 On a database with demo data

The demo data publishes a **FastAPI Demo Endpoint** on `/fastapi_demo`. Open
`http://<your-odoo>/fastapi_demo/docs` and try the routes; the authenticated
ones accept your Odoo login and password (HTTP Basic).

### 2.2 The starter template

`fast_api/examples/starter_api` is a complete, tested API module:

| Route | Auth | What it does |
|---|---|---|
| `GET /starter_api/health` | none | `{"status": "ok"}` |
| `GET /starter_api/me` | API key | the user who owns the key |
| `GET /starter_api/partners?search=&page=&page_size=` | API key | paged list of contacts |
| `GET /starter_api/partners/{id}` | API key | one contact, 404 if not found |
| `POST /starter_api/partners` | API key | create a contact (validated body) |

Every route runs **as the user who owns the API key**, so that user's access
rights and record rules apply exactly as in the web client.

```bash
cp -r fast_api/examples/starter_api /path/to/your/addons/
# restart Odoo, Update Apps List, install "Starter API"
```

Create a key in Odoo (*avatar > Preferences > Account Security > New API
Key*), then:

```bash
curl -H "Authorization: Bearer <your key>" http://localhost:8069/starter_api/me
curl -H "X-API-Key: <your key>" "http://localhost:8069/starter_api/partners?search=deco"
curl -X POST -H "Authorization: Bearer <your key>" -H "Content-Type: application/json" \
     -d '{"name": "ACME", "email": "info@acme.com"}' http://localhost:8069/starter_api/partners
```

Interactive documentation: `http://localhost:8069/starter_api/docs`.

---

## 3. Build your own API

Copy the starter, rename the folder and `starter`/`starter_api` in it, then
change these four pieces.

**`__manifest__.py`** depends on `fast_api` (plus your business modules).

**`models/fastapi_endpoint.py`** registers the app and its routers:

```python
from odoo import fields, models

from ..routers import order_router


class FastapiEndpoint(models.Model):
    _inherit = "fastapi.endpoint"

    app = fields.Selection(
        selection_add=[("shop", "Shop API")], ondelete={"shop": "cascade"}
    )

    def _get_fastapi_routers(self):
        if self.app == "shop":
            return [order_router]
        return super()._get_fastapi_routers()
```

**`routers/orders.py`** contains plain FastAPI code. Get Odoo through
dependencies:

```python
from typing import Annotated

from odoo.api import Environment
from odoo.addons.fast_api.dependencies import api_key_user_env

from fastapi import APIRouter, Depends
from pydantic import BaseModel

order_router = APIRouter(tags=["orders"])


class Order(BaseModel):
    id: int
    name: str
    amount_total: float


@order_router.get("/orders")
def my_orders(env: Annotated[Environment, Depends(api_key_user_env)]) -> list[Order]:
    orders = env["sale.order"].search([], limit=20)
    return [Order(id=o.id, name=o.name, amount_total=o.amount_total) for o in orders]
```

**`data/fastapi_endpoint.xml`** creates the endpoint record, the user it runs
as, and publishes it at install (see the starter's file for the full version):

```xml
<record id="endpoint_shop" model="fastapi.endpoint">
    <field name="name">Shop API</field>
    <field name="app">shop</field>
    <field name="root_path">/api/shop/v1</field>
    <field name="user_id" ref="user_shop_api"/>
    <field name="save_http_session" eval="False"/>
</record>
<function model="fastapi.endpoint" name="action_sync_registry" eval="[[ref('endpoint_shop')]]"/>
```

### 3.1 How an endpoint is served

- An endpoint record mounts one app on its **root path**. Its routes only
  answer once the endpoint is **synced**: the form shows *Sync Registry* until
  then, and unsynced routes return 404. Creating the record alone is not
  enough; the `<function ... action_sync_registry>` line above does it at
  install.
- Editing the root path, the session setting or archiving the endpoint marks
  it out of sync again. Other settings (and fields your module lists in
  `_fastapi_app_fields()`) rebuild the app in every worker on the next request.
- The **user** of the endpoint is the identity the app runs as before a
  request is authenticated. Give it only the *FastAPI Endpoint Runner* group
  (or a group implying it): it can read its own user and endpoint, and the
  partner your authentication returned. Do not use an internal user here.
- For a stateless API (API keys, JWT) untick **Save HTTP Session**, so no
  session file is written per call.
- Python changes need an Odoo restart, as for any module.

### 3.2 Dependencies you can use in a route

All live in `odoo.addons.fast_api.dependencies`.

| Dependency | Gives you |
|---|---|
| `odoo_env` | the Odoo environment of the request (endpoint user, request language, endpoint company) |
| `api_key_user` | the `res.users` owning the API key sent as `Authorization: Bearer <key>` or `X-API-Key: <key>`; 401 otherwise |
| `api_key_user_env` | an environment running **as that user**, with their access rights |
| `basic_auth_user` | the `res.users` authenticated by HTTP Basic (login + password or API key); 401 otherwise |
| `authenticated_partner` | the partner returned by your authentication (see 3.3) |
| `authenticated_partner_env` | an environment whose record rules can use `authenticated_partner_id` |
| `optionally_authenticated_partner` | same, or `None` for anonymous calls |
| `paging` | `page` / `page_size` query parameters as a `Paging(limit, offset)` |
| `fastapi_endpoint` | the `fastapi.endpoint` record serving the request |

`odoo.addons.fast_api.schemas.PagedCollection[T]` is a ready-made
`{"count": ..., "items": [...]}` response model.

### 3.3 Authentication

**Run as the API key owner** (simplest; what the starter does): depend on
`api_key_user_env`. Users create and revoke their own keys in Odoo; an expired
key or an archived user is refused.

**Authenticated partner** (for customer or portal facing APIs): the app keeps
running as the endpoint user and record rules filter on the authenticated
partner. Choose how the partner is found by overriding
`authenticated_partner_impl` when the app is built:

```python
from odoo.addons.fast_api.dependencies import (
    authenticated_partner_from_api_key_user,  # Odoo API key
    authenticated_partner_from_basic_auth_user,  # HTTP Basic
    authenticated_partner_impl,
)


class FastapiEndpoint(models.Model):
    _inherit = "fastapi.endpoint"

    def _get_app(self):
        app = super()._get_app()
        if self.app == "shop":
            app.dependency_overrides[authenticated_partner_impl] = (
                authenticated_partner_from_api_key_user
            )
        return app
```

Any other scheme (JWT, OAuth2, HMAC signatures) is a function returning a
`res.partner`, plugged the same way.

### 3.4 Errors

| Raised in your code | HTTP status | Body |
|---|---|---|
| `UserError`, `ValidationError` | 400 | `{"detail": "<message>"}` |
| `AccessError`, `AccessDenied` | 403 | `{"detail": "<message>"}` |
| `MissingError` | 404 | `{"detail": "<message>"}` |
| `fastapi.HTTPException(status_code=...)` | that status | `{"detail": ...}` |
| invalid request (Pydantic) | 422 | the validation errors |
| anything else | 500 | `{"detail": "Internal Server Error"}` |

On any error the database transaction is rolled back. Concurrency errors
(serialization failures) are retried by Odoo, request body included.

### 3.5 Language

The `Accept-Language` header selects the language of the request (`fr-BE`,
`fr`, ...) among the languages installed in Odoo, so translated fields and
messages come back in that language.

### 3.6 CORS, middlewares, app settings

Override `_get_fastapi_app_middlewares()` to add Starlette middlewares (for
example `CORSMiddleware`) and `_prepare_fastapi_app_params()` to pass options
to the `FastAPI(...)` constructor (OpenAPI tags, version, ...).

---

## 4. Test your API

`FastAPITransactionCase` runs a router in-process, inside the test
transaction, without an HTTP server:

```python
from odoo.addons.fast_api.tests.common import FastAPITransactionCase

from ..routers import order_router


class TestOrders(FastAPITransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.default_fastapi_router = order_router
        cls.default_fastapi_running_user = cls.env.ref("my_api.user_shop_api")

    def test_orders(self):
        key = self.env["res.users.apikeys"].with_user(self.env.ref("base.user_admin")).sudo()._generate(None, "test", None)
        with self._create_test_client() as client:
            response = client.get("/orders", headers={"X-API-Key": key})
        self.assertEqual(response.status_code, 200)
```

The starter's `tests/test_partners.py` is a complete example. Starlette's test
client needs `httpx2` (or `httpx`) in the environment where tests run.

Odoo 18's `authenticate()` (used by HTTP Basic) opens a database cursor of its
own. In a test, route it to the test transaction first, or it will not see
the users your test creates:

```python
self.registry.enter_test_mode(self.env.cr)
self.addCleanup(self.registry.leave_test_mode)
```

---

## 5. Good to know

- **This module replaces OCA's `fastapi` and `endpoint_route_handler`.** It
  declares the same models, so it refuses to install while they are installed.
  Code written for them ports by changing `depends` to `fast_api` and imports
  from `odoo.addons.fastapi` to `odoo.addons.fast_api`.
- **The `/docs` page is blank**: Swagger UI and ReDoc load their JavaScript
  from the jsDelivr CDN in the browser. The API itself works without it.
- **Logging**: client errors raised by FastAPI (401, 409, 422, ...) are logged
  as one INFO line; Odoo exceptions keep Odoo's usual WARNING; anything that
  becomes a 500 is logged as an ERROR with its traceback.
- **Uninstalling** removes the endpoints and the route table; routes stop
  answering immediately.

---

## 6. Credits and licence

Built on the FastAPI integration of the Odoo Community Association:
`fastapi` (ACSONE SA/NV) and `endpoint_route_handler` (Camptocamp SA), merged
into one module, with Odoo API key authentication, install and uninstall
hooks, and a starter template added by Albatross.

Licence: LGPL-3.

Support: <connect@albatross.work> · <https://albatross.work>. We answer within
one business day and fix confirmed bugs free of charge for 90 days after
purchase.
