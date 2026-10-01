# Copyright 2022 ACSONE SA/NV
# Copyright 2021 Camptocamp SA
# Copyright 2026 Albatross
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

{
    "name": "FastAPI - REST API Framework",
    "summary": "Build REST APIs inside Odoo with FastAPI: Swagger UI & ReDoc, "
    "OpenAPI schema, API key and HTTP Basic auth, Pydantic validation, "
    "JSON errors",
    "description": """
FastAPI - REST API Framework
============================

Serve REST APIs written with FastAPI from your Odoo server, on the same port,
with the same users, access rights and database transaction as the web client.

* Declare an API as an endpoint record mounted on any path (/api/v1, /shop, ...)
* Interactive documentation for every API: Swagger UI, ReDoc and openapi.json
* Ready-made authentication: Odoo API keys or HTTP Basic, or plug your own
* Pydantic request and response validation
* Odoo exceptions mapped to JSON errors (400, 401, 403, 404, 422, 500)
* Transaction rolled back on error, automatic retry on concurrency errors
* Accept-Language header honoured for translated responses
* Record rules aware of the authenticated partner
* Test helper class to unit-test your routers without an HTTP server

Built on the FastAPI framework of the Odoo Community Association
(ACSONE SA/NV, Camptocamp), packaged as a single module.
""",
    "version": "18.0.1.0.0",
    "category": "Extra Tools",
    "author": "Albatross",
    "website": "https://albatross.work",
    "support": "connect@albatross.work",
    "license": "LGPL-3",
    "price": 15.82,
    "currency": "EUR",
    "depends": ["base", "web"],
    "external_dependencies": {
        "python": [
            "fastapi>=0.110.0",
            "pydantic>=2.0",
            "python-multipart",
            "ujson",
            "a2wsgi>=1.10.6",
            "parse-accept-language",
        ]
    },
    "data": [
        "security/res_groups.xml",
        "security/ir.model.access.csv",
        "security/ir_rule.xml",
        "views/fastapi_menu.xml",
        "views/fastapi_endpoint.xml",
        "views/fastapi_endpoint_demo.xml",
    ],
    "demo": ["demo/fastapi_endpoint_demo.xml"],
    "images": ["static/description/banner.png"],
    "pre_init_hook": "pre_init_hook",
    "post_init_hook": "post_init_hook",
    "uninstall_hook": "uninstall_hook",
    "installable": True,
    "application": True,
}
