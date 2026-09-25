from __future__ import annotations

import os
import smtplib
import ssl
from email.message import EmailMessage
from datetime import datetime, timezone
from uuid import uuid4

from backend.app.database.client import supabase


def _now():
    return datetime.now(timezone.utc).isoformat()


def _application_number() -> str:
    return f"MM-BIS-{datetime.now(timezone.utc):%Y%m%d}-{uuid4().hex[:6].upper()}"


def _owned(application_id: str, user_id: str):
    result = (
        supabase.table("certification_applications")
        .select("*")
        .eq("id", application_id)
        .eq("user_id", user_id)
        .maybe_single()
        .execute()
    )
    return result.data


def create_application(user_id: str, payload: dict):
    row = {
        "user_id": user_id,
        "application_number": _application_number(),
        "status": "draft",
        "current_step": 1,
        "product_name": payload.get("product_name"),
        "is_number": payload.get("is_number"),
        "company_name": payload.get("company_name"),
        "contact_email": payload.get("contact_email"),
        "applicant_name": payload.get("applicant_name"),
        "phone": payload.get("phone"),
        "factory_address": payload.get("factory_address"),
        "data": payload.get("data") or {},
        "document_ids": payload.get("document_ids") or [],
        "email_status": "not_sent",
        "created_at": _now(),
        "updated_at": _now(),
    }
    return supabase.table("certification_applications").insert(row).execute().data[0]


def update_application(application_id: str, user_id: str, payload: dict):
    existing = _owned(application_id, user_id)
    if not existing:
        return None

    row = {k: v for k, v in {
        "current_step": payload.get("current_step"),
        "status": payload.get("status"),
        "product_name": payload.get("product_name"),
        "is_number": payload.get("is_number"),
        "company_name": payload.get("company_name"),
        "contact_email": payload.get("contact_email"),
        "applicant_name": payload.get("applicant_name"),
        "phone": payload.get("phone"),
        "factory_address": payload.get("factory_address"),
        "data": payload.get("data"),
        "document_ids": payload.get("document_ids"),
        "updated_at": _now(),
    }.items() if v is not None}

    return (
        supabase.table("certification_applications")
        .update(row)
        .eq("id", application_id)
        .eq("user_id", user_id)
        .execute()
        .data[0]
    )


def list_applications(user_id: str):
    return (
        supabase.table("certification_applications")
        .select("*")
        .eq("user_id", user_id)
        .order("updated_at", desc=True)
        .execute()
        .data
    )


def send_application_email(application: dict):
    host = os.getenv("SMTP_HOST", "").strip()
    port = int(os.getenv("SMTP_PORT", "587"))
    username = os.getenv("SMTP_USERNAME", "").strip()
    password = os.getenv("SMTP_PASSWORD", "")
    sender = os.getenv("SMTP_FROM", username).strip()
    recipient = (application.get("contact_email") or "").strip()

    if not recipient:
        return {"sent": False, "status": "not_configured", "message": "No contact email was supplied."}
    if not all([host, username, password, sender]):
        return {
            "sent": False,
            "status": "not_configured",
            "message": "SMTP is not configured. Add SMTP_HOST, SMTP_USERNAME, SMTP_PASSWORD and SMTP_FROM to the backend environment.",
        }

    app_no = application["application_number"]
    msg = EmailMessage()
    msg["Subject"] = f"ManakMitra BIS application saved — {app_no}"
    msg["From"] = sender
    msg["To"] = recipient
    msg.set_content(
        "Your ManakMitra BIS product-certification application has been saved.\n\n"
        f"Application number: {app_no}\n"
        f"Product: {application.get('product_name') or '—'}\n"
        f"Indian Standard: {application.get('is_number') or '—'}\n"
        f"Company: {application.get('company_name') or '—'}\n\n"
        "You can return to ManakMitra and continue the four-step preparation workflow. "
        "ManakMitra does not represent that this draft has been submitted to BIS. "
        "Official online submission is completed through the BIS ManakOnline portal.\n"
    )

    context = ssl.create_default_context()
    try:
        if port == 465:
            with smtplib.SMTP_SSL(host, port, context=context, timeout=20) as smtp:
                smtp.login(username, password)
                smtp.send_message(msg)
        else:
            with smtplib.SMTP(host, port, timeout=20) as smtp:
                smtp.ehlo()
                smtp.starttls(context=context)
                smtp.ehlo()
                smtp.login(username, password)
                smtp.send_message(msg)
        return {"sent": True, "status": "sent", "message": "Email sent successfully."}
    except Exception as exc:
        return {"sent": False, "status": "failed", "message": f"Email delivery failed: {str(exc)[:240]}"}
