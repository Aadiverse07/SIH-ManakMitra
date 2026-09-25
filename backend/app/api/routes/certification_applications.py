from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel, Field

from backend.app.services.auth import authenticated_user_id
from backend.app.services.certification_applications import (
    create_application,
    list_applications,
    send_application_email,
    update_application,
    _owned,
)

router = APIRouter(prefix="/certification-applications", tags=["certification-applications"])


class ApplicationPayload(BaseModel):
    current_step: int = Field(1, ge=1, le=4)
    status: str = "draft"
    product_name: str | None = None
    is_number: str | None = None
    company_name: str | None = None
    contact_email: str | None = None
    applicant_name: str | None = None
    phone: str | None = None
    factory_address: str | None = None
    data: dict = Field(default_factory=dict)
    document_ids: list[str] = Field(default_factory=list)


def _user(authorization: str | None):
    return authenticated_user_id(authorization)


@router.get("")
def get_applications(authorization: str | None = Header(None)):
    return list_applications(_user(authorization))


@router.post("")
def create_application_route(payload: ApplicationPayload, authorization: str | None = Header(None)):
    # Applications are created after Step 1 (applicant/company details), before the
    # product name and contact email are collected in Step 2. Requiring those fields
    # here would make it impossible to ever save a draft, so only authentication is
    # required at creation time; the frontend enforces per-step required fields.
    user_id = _user(authorization)
    return create_application(user_id, payload.model_dump())


@router.get("/{application_id}")
def get_application(application_id: str, authorization: str | None = Header(None)):
    app = _owned(application_id, _user(authorization))
    if not app:
        raise HTTPException(404, "Application not found.")
    return app


@router.patch("/{application_id}")
def update_application_route(application_id: str, payload: ApplicationPayload, authorization: str | None = Header(None)):
    updated = update_application(application_id, _user(authorization), payload.model_dump())
    if not updated:
        raise HTTPException(404, "Application not found.")
    return updated


@router.post("/{application_id}/email")
def email_application(application_id: str, authorization: str | None = Header(None)):
    app = _owned(application_id, _user(authorization))
    if not app:
        raise HTTPException(404, "Application not found.")
    result = send_application_email(app)
    # Persist status, but never report a false success.
    update_application(application_id, _user(authorization), {"data": app.get("data") or {}, "status": app.get("status", "draft")})
    from backend.app.database.client import supabase
    supabase.table("certification_applications").update({
        "email_status": result["status"],
        "email_error": None if result["sent"] else result["message"],
    }).eq("id", application_id).eq("user_id", _user(authorization)).execute()
    return result
