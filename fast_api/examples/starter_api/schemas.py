from pydantic import BaseModel, Field


class UserOut(BaseModel):
    id: int
    name: str
    login: str

    @classmethod
    def from_user(cls, user):
        return cls(id=user.id, name=user.name, login=user.login)


class PartnerOut(BaseModel):
    id: int
    name: str
    email: str | None = None
    phone: str | None = None
    is_company: bool

    @classmethod
    def from_partner(cls, partner):
        # Odoo returns False for empty fields: send null instead.
        return cls(
            id=partner.id,
            name=partner.name or "",
            email=partner.email or None,
            phone=partner.phone or None,
            is_company=partner.is_company,
        )


class PartnerIn(BaseModel):
    name: str = Field(min_length=1, max_length=128)
    email: str | None = None
    phone: str | None = None
