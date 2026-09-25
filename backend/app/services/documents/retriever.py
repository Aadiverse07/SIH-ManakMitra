"""Private structured-document retrieval for the Ask AI pipeline."""
from __future__ import annotations
import re
from typing import Any
from backend.app.database.client import supabase


def _score(text: str, query: str) -> float:
    hay = text.lower()
    terms = [t for t in re.findall(r"[a-z0-9.]+", query.lower()) if len(t) > 1]
    if not terms:
        return 0.0
    return sum(1.0 for t in terms if t in hay) / len(terms)


def search_user_documents(user_id: str, query: str, top_k: int = 6) -> list[dict[str, Any]]:
    if not user_id or not query.strip():
        return []
    # First retrieve chunks because they preserve the broad textual context.
    docs = supabase.table("documents").select("id,title,standard_number,revision,document_version,source,source_url,publication_date").eq("owner_user_id", user_id).eq("processing_status", "processed").limit(50).execute().data or []
    if not docs:
        return []
    doc_ids = [d["id"] for d in docs]
    by_id = {d["id"]: d for d in docs}
    q = f"%{query.strip()}%"
    rows = supabase.table("document_chunks").select("*").in_("document_id", doc_ids).or_(f"content.ilike.{q},clause.ilike.{q},section.ilike.{q}").limit(max(top_k * 5, 20)).execute().data or []
    results = []
    for row in rows:
        doc = by_id.get(row.get("document_id"), {})
        text = row.get("content", "")
        results.append({
            **row,
            "content": text,
            "number": doc.get("standard_number"),
            "title": doc.get("title"),
            "standard_title": doc.get("title"),
            "document_version": doc.get("document_version") or doc.get("revision"),
            "version": doc.get("document_version") or doc.get("revision"),
            "source": doc.get("source") or "User document",
            "source_url": doc.get("source_url"),
            "source_publication_date": doc.get("publication_date"),
            "knowledge_type": "document_chunk",
            "knowledge_id": row.get("id"),
            "retrieval": {"knowledge_type": "document_chunk", "hybrid_score": _score(text + " " + str(row.get("clause") or ""), query)},
        })

    # Structured entities are queried separately so formulas/tables/requirements
    # can be returned even when their text is not an exact chunk match.
    entity_specs = [
        ("document_formulas", "expression_plain,expression_latex,source_text", "formula"),
        ("document_tables", "title,raw_text,table_number", "table"),
        ("document_requirements", "statement,evidence,classification", "requirement"),
        ("document_definitions", "term,definition", "definition"),
        ("document_clauses", "clause_number,title,text_content", "clause"),
    ]
    for table, fields, kind in entity_specs:
        ors = ",".join(f"{field}.ilike.{q}" for field in fields.split(","))
        entity_rows = supabase.table(table).select("*").in_("document_id", doc_ids).or_(ors).limit(max(top_k * 3, 12)).execute().data or []
        for row in entity_rows:
            doc = by_id.get(row.get("document_id"), {})
            if kind == "formula":
                content = row.get("expression_plain") or row.get("expression_latex") or row.get("source_text") or ""
            elif kind == "table":
                content = row.get("raw_text") or row.get("title") or ""
            elif kind == "requirement":
                content = row.get("statement") or ""
            elif kind == "definition":
                content = f"{row.get('term','')}: {row.get('definition','')}"
            else:
                content = row.get("text_content") or row.get("title") or ""
            results.append({
                **row, "content": content, "number": doc.get("standard_number"),
                "title": doc.get("title"), "standard_title": doc.get("title"),
                "document_version": doc.get("document_version") or doc.get("revision"),
                "version": doc.get("document_version") or doc.get("revision"),
                "source": doc.get("source") or "User document", "source_url": doc.get("source_url"),
                "source_publication_date": doc.get("publication_date"),
                "knowledge_type": f"document_{kind}", "knowledge_id": row.get("id"),
                "retrieval": {"knowledge_type": f"document_{kind}", "hybrid_score": min(1.0, _score(content, query) + 0.15)},
            })
    # Deduplicate by evidence ID, then rank structured evidence first on exact matches.
    unique = {}
    for item in results:
        key = (item.get("knowledge_id"), item.get("knowledge_type"))
        unique[key] = item
    return sorted(unique.values(), key=lambda r: (-float(r.get("retrieval", {}).get("hybrid_score", 0)), r.get("page_number") or 0))[:top_k]
