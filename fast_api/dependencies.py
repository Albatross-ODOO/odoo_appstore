# Copyright 2022 ACSONE SA/NV
# Copyright 2026 Albatross (Odoo API key authentication)
# License LGPL-3.0 or later (http://www.gnu.org/licenses/LGPL).

from typing import Annotated

from odoo.api import Environment
from odoo.exceptions import AccessDenied

from odoo.addons.base.models.res_partner import ResPartner
from odoo.addons.base.models.res_users import ResUsers

from fastapi import Depends, Header, HTTPException, Query, status
from fastapi.security import (
    APIKeyHeader,
    HTTPAuthorizationCredentials,
    HTTPBasic,
    HTTPBasicCredentials,
    HTTPBearer,
)

from .context import odoo_env_ctx
from .models.fastapi_endpoint import FastapiEndpoint
from .schemas import Paging


def company_id() -> int | None:
    """This method may be overriden by the FastAPI app to set the allowed company
    in the Odoo env of the endpoint. By default, the company defined on the
    endpoint record is used.
    """
    return None


def odoo_env(company_id: Annotated[int | None, Depends(company_id)]) -> Environment:
    env = odoo_env_ctx.get()
    if company_id is not None:
        env = env(context=dict(env.context, allowed_company_ids=[company_id]))

    yield env


def authenticated_partner_impl() -> ResPartner:
    """This method has to be overriden when you create your fastapi app
    to declare the way your partner will be provided. In some case, this
    partner will come from the authentication mechanism (ex jwt token) in other cases
    it could comme from a lookup on an email received into an HTTP header ...
    See the fastapi_endpoint_demo for an example"""


def optionally_authenticated_partner_impl() -> ResPartner | None:
    """This method has to be overriden when you create your fastapi app
    and you need to get an optional authenticated partner into your endpoint.
    """


def authenticated_partner_env(
    partner: Annotated[ResPartner, Depends(authenticated_partner_impl)],
) -> Environment:
    """Return an environment with the authenticated partner id in the context"""
    return partner.with_context(authenticated_partner_id=partner.id).env


def optionally_authenticated_partner_env(
    partner: Annotated[
        ResPartner | None, Depends(optionally_authenticated_partner_impl)
    ],
    env: Annotated[Environment, Depends(odoo_env)],
) -> Environment:
    """Return an environment with the authenticated partner id in the context if
    the partner is not None
    """
    if partner:
        return partner.with_context(authenticated_partner_id=partner.id).env
    return env


def authenticated_partner(
    partner: Annotated[ResPartner, Depends(authenticated_partner_impl)],
    partner_env: Annotated[Environment, Depends(authenticated_partner_env)],
) -> ResPartner:
    """If you need to get access to the authenticated partner into your
    endpoint, you can add a dependency into the endpoint definition on this
    method.
    This method is a safe way to declare a dependency without requiring a
    specific implementation. It depends on `authenticated_partner_impl`. The
    concrete implementation of authenticated_partner_impl has to be provided
    when the FastAPI app is created.
    This method return a partner into the authenticated_partner_env
    """
    return partner_env["res.partner"].browse(partner.id)


def optionally_authenticated_partner(
    partner: Annotated[
        ResPartner | None, Depends(optionally_authenticated_partner_impl)
    ],
    partner_env: Annotated[Environment, Depends(optionally_authenticated_partner_env)],
) -> ResPartner | None:
    """If you need to get access to the authenticated partner if the call is
    authenticated, you can add a dependency into the endpoint definition on this
    method.

    This method defer from authenticated_partner by the fact that it returns
    None if the partner is not authenticated .
    """
    if partner:
        return partner_env["res.partner"].browse(partner.id)
    return None


def paging(
    page: Annotated[int, Query(ge=1)] = 1, page_size: Annotated[int, Query(ge=1)] = 80
) -> Paging:
    """Return a Paging object from the page and page_size parameters"""
    return Paging(limit=page_size, offset=(page - 1) * page_size)


def basic_auth_user(
    credential: Annotated[HTTPBasicCredentials, Depends(HTTPBasic())],
    env: Annotated[Environment, Depends(odoo_env)],
) -> ResUsers:
    username = credential.username
    password = credential.password
    try:
        response = (
            env["res.users"]
            .sudo()
            .authenticate(
                credential={
                    "type": "password",
                    "login": username,
                    "password": password,
                },
                user_agent_env={"interactive": False},
            )
        )
        return env["res.users"].browse(response.get("uid"))
    except AccessDenied as ad:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Basic"},
        ) from ad


def authenticated_partner_from_basic_auth_user(
    user: Annotated[ResUsers, Depends(basic_auth_user)],
    env: Annotated[Environment, Depends(odoo_env)],
) -> ResPartner:
    return env["res.partner"].browse(user.sudo().partner_id.id)


def api_key_user(
    bearer: Annotated[
        HTTPAuthorizationCredentials | None,
        Depends(
            HTTPBearer(
                auto_error=False,
                description="An Odoo API key, sent as `Authorization: Bearer <key>`.",
            )
        ),
    ],
    api_key: Annotated[
        str | None,
        Depends(
            APIKeyHeader(
                name="X-API-Key",
                auto_error=False,
                description="An Odoo API key, sent as `X-API-Key: <key>`.",
            )
        ),
    ],
    env: Annotated[Environment, Depends(odoo_env)],
) -> ResUsers:
    """Return the user owning the Odoo API key sent with the request.

    The keys are Odoo's own: a user creates one in *Preferences > Security
    > Create API Key*, the same key that XML-RPC and JSON-RPC accept.
    Expired keys and keys of archived users are refused. The key may be sent
    as ``Authorization: Bearer <key>`` or as ``X-API-Key: <key>``.
    """
    key = (bearer.credentials if bearer else None) or api_key
    uid = None
    if key:
        uid = env["res.users.apikeys"].sudo()._check_credentials(scope="rpc", key=key)
    if not uid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return env["res.users"].browse(uid)


def api_key_user_env(
    user: Annotated[ResUsers, Depends(api_key_user)],
    env: Annotated[Environment, Depends(odoo_env)],
) -> Environment:
    """Return an environment running as the owner of the API key.

    Everything done with this environment obeys that user's access rights
    and record rules, exactly as in the web client. The companies allowed
    by the endpoint are kept when the user belongs to them, otherwise the
    user's default company is used.
    """
    user = user.sudo()
    company_ids = [
        cid
        for cid in env.context.get("allowed_company_ids") or []
        if cid in user.company_ids.ids
    ] or user.company_id.ids
    return env(user=user.id, context=dict(env.context, allowed_company_ids=company_ids))


def authenticated_partner_from_api_key_user(
    user: Annotated[ResUsers, Depends(api_key_user)],
    env: Annotated[Environment, Depends(odoo_env)],
) -> ResPartner:
    """The partner of the API key's owner, to plug into
    ``authenticated_partner_impl``."""
    return env["res.partner"].browse(user.sudo().partner_id.id)


def fastapi_endpoint_id() -> int:
    """This method is overriden by the FastAPI app to make the fastapi.endpoint record
    available for your endpoint method. To get the fastapi.endpoint record
    in your method, you just need to add a dependency on the fastapi_endpoint method
    defined below
    """


def fastapi_endpoint(
    _id: Annotated[int, Depends(fastapi_endpoint_id)],
    env: Annotated[Environment, Depends(odoo_env)],
) -> "FastapiEndpoint":
    """Return the fastapi.endpoint record"""
    return env["fastapi.endpoint"].browse(_id)


def accept_language(
    accept_language: Annotated[
        str | None,
        Header(
            alias="Accept-Language",
            description="The Accept-Language header is used to specify the language "
            "of the content to be returned. If a language is not available, the "
            "server will return the content in the default language.",
        ),
    ] = None,
) -> str:
    """This dependency is used at application level to document the way the language
    to use for the response is specified. The header is processed outside of the
    fastapi app to initialize the odoo environment with the right language.
    """
    return accept_language
