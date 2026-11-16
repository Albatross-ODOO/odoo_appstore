from typing import Annotated

from odoo.api import Environment
from odoo.exceptions import MissingError

from odoo.addons.fast_api.dependencies import api_key_user_env, paging
from odoo.addons.fast_api.schemas import PagedCollection, Paging

from fastapi import APIRouter, Depends, Query, status

from ..schemas import PartnerIn, PartnerOut, UserOut

# Every route of this router needs an Odoo API key, and runs as the user who
# owns it: that user's access rights and record rules apply.
router = APIRouter(tags=["partners"])

UserEnv = Annotated[Environment, Depends(api_key_user_env)]


@router.get("/me")
def me(env: UserEnv) -> UserOut:
    """The user behind the API key."""
    return UserOut.from_user(env.user)


@router.get("/partners")
def list_partners(
    env: UserEnv,
    page: Annotated[Paging, Depends(paging)],
    search: Annotated[str | None, Query(description="Part of a name or email")] = None,
) -> PagedCollection[PartnerOut]:
    """Contacts the user can read, 80 per page by default."""
    domain = []
    if search:
        domain = ["|", ("name", "ilike", search), ("email", "ilike", search)]
    partners = env["res.partner"].search(
        domain, limit=page.limit, offset=page.offset, order="name, id"
    )
    return PagedCollection[PartnerOut](
        count=env["res.partner"].search_count(domain),
        items=[PartnerOut.from_partner(p) for p in partners],
    )


@router.get("/partners/{partner_id}")
def get_partner(env: UserEnv, partner_id: int) -> PartnerOut:
    """One contact. 404 if it does not exist or the user cannot see it."""
    partner = env["res.partner"].search([("id", "=", partner_id)])
    if not partner:
        raise MissingError(f"Contact {partner_id} not found.")
    return PartnerOut.from_partner(partner)


@router.post("/partners", status_code=status.HTTP_201_CREATED)
def create_partner(env: UserEnv, data: PartnerIn) -> PartnerOut:
    """Create a contact. The body is validated before any Odoo code runs."""
    partner = env["res.partner"].create(data.model_dump())
    return PartnerOut.from_partner(partner)
