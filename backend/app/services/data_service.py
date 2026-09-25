"""Database-backed operations for the existing API contract."""
from backend.app.database.client import supabase

def _provenance(r):
    return {
        "knowledge_status": r.get("knowledge_status", "official_verified"),
        "source": r.get("source"),
        "source_url": r.get("source_url"),
        "source_updated_at": r.get("source_updated_at"),
        "created_at": r.get("created_at"),
        "updated_at": r.get("updated_at"),
    }

def row_to_standard(r):
    return {"number": r["is_number"], "title": r["title"], "desc": r.get("description"),
            "category": r.get("category"), "dept": r.get("dept"), "status": r.get("status", "Active"),
            "reaffirmed": r.get("reaffirmed"), "language": r.get("language"),
            "superseded_by": r.get("superseded_by"),
            "version_id": r.get("version_id"), "version_label": r.get("version_label"),
            "publication_year": r.get("publication_year"), "version_kind": r.get("version_kind"),
            "current_verified": r.get("current_verified", False), **_provenance(r)}

def row_to_service(r):
    return {"id": r["id"], "name": r["name"], "summary": r.get("summary"),
            "detail": r.get("detail"), "icon": r.get("icon"), **_provenance(r)}

def row_to_faq(r):
    return {"q": r["question"], "a": r["answer"], "category": r.get("category"), **_provenance(r)}

def row_to_lab(r):
    return {"name": r["name"], "city": r.get("city"), "scope": r.get("scope"),
            "status": r.get("status", "Recognised"), **_provenance(r)}

def row_to_cert_step(r):
    return {"step": r["step"], "title": r["title"], "detail": r.get("detail"), **_provenance(r)}

def row_to_license(r):
    return {"license_number": r["license_number"], "holder_name": r["holder_name"],
            "product_or_standard": r.get("product_or_standard"), "status": r.get("status", "active"),
            "valid_until": r.get("valid_until"), **_provenance(r)}

def list_standards(q=None, category=None, status=None):
    query = supabase.table("standards").select("*")
    if category:
        query = query.eq("category", category)
    if status:
        query = query.eq("status", status)
    if q:
        like = f"%{q}%"
        query = query.or_(f"is_number.ilike.{like},title.ilike.{like},description.ilike.{like},category.ilike.{like},dept.ilike.{like}")
    return [row_to_standard(r) for r in query.order("is_number").execute().data]

def get_standard(number):
    data = supabase.table("standards").select("*").eq("is_number", number).limit(1).execute().data
    return row_to_standard(data[0]) if data else None

def list_services():
    return [row_to_service(r) for r in supabase.table("services").select("*").order("name").execute().data]

def get_service(service_id):
    data = supabase.table("services").select("*").eq("id", service_id).limit(1).execute().data
    return row_to_service(data[0]) if data else None

def list_faqs():
    return [row_to_faq(r) for r in supabase.table("faqs").select("*").order("id").execute().data]

def list_labs():
    return [row_to_lab(r) for r in supabase.table("labs").select("*").order("id").execute().data]

def list_cert_steps():
    return [row_to_cert_step(r) for r in supabase.table("cert_steps").select("*").order("step").execute().data]

def get_license(number):
    data = supabase.table("licenses").select("*").eq("license_number", number).limit(1).execute().data
    return row_to_license(data[0]) if data else None

def _to_e164_in(phone):
    p = phone.strip()
    return p if p.startswith("+") else f"+91{p.lstrip('0')}"

def check_availability(email=None, phone=None):
    email_norm = email.strip().lower() if email else None
    phone_norm = _to_e164_in(phone) if phone else None
    email_taken = phone_taken = False
    page, per_page = 1, 1000
    while True:
        result = supabase.auth.admin.list_users(page=page, per_page=per_page)
        users = result if isinstance(result, list) else getattr(result, "users", None) or []
        if not users: break
        for u in users:
            u_email = (getattr(u, "email", None) or "").strip().lower()
            u_phone = (getattr(u, "phone", None) or "").strip()
            if email_norm and u_email == email_norm: email_taken = True
            if phone_norm and u_phone and (u_phone == phone_norm or f"+{u_phone.lstrip('+')}" == phone_norm): phone_taken = True
        if len(users) < per_page: break
        page += 1
    return {"email_taken": email_taken, "phone_taken": phone_taken}
