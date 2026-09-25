"""Persistence and retrieval for Phase 20 structured document entities."""
from __future__ import annotations
from backend.app.database.client import supabase

TABLES = (
    "document_sections", "document_clauses", "document_definitions",
    "document_tables", "document_formulas", "document_requirements",
)

class StructuredDocumentRepository:
    def owned(self, user_id: str, document_id: str) -> bool:
        rows = supabase.table("documents").select("id").eq("id", document_id).eq("owner_user_id", user_id).limit(1).execute().data or []
        return bool(rows)

    def clear(self, document_id: str):
        for table in TABLES:
            supabase.table(table).delete().eq("document_id", document_id).execute()

    def insert(self, table: str, rows: list[dict]):
        if rows:
            return supabase.table(table).insert(rows).execute().data or []
        return []

    def list_for_document(self, user_id: str, document_id: str, table: str, limit: int = 200):
        if table not in TABLES or not self.owned(user_id, document_id):
            return []
        return supabase.table(table).select("*").eq("document_id", document_id).order("page_number").limit(limit).execute().data or []

    def search(self, user_id: str, document_id: str, query: str, entity: str = "all", limit: int = 20):
        if not self.owned(user_id, document_id):
            return []
        tables = TABLES if entity == "all" else (("document_" + entity),)
        q = f"%{query}%"
        out = []
        for table in tables:
            if table not in TABLES:
                continue
            fields = {
                "document_sections": ["title", "section_number"],
                "document_clauses": ["clause_number", "title", "text_content"],
                "document_definitions": ["term", "definition"],
                "document_tables": ["table_number", "title", "raw_text"],
                "document_formulas": ["expression_plain", "expression_latex", "source_text"],
                "document_requirements": ["statement", "classification", "evidence"],
            }[table]
            expression = ",".join(f"{field}.ilike.{q}" for field in fields)
            rows = supabase.table(table).select("*").eq("document_id", document_id).or_(expression).limit(limit).execute().data or []
            for row in rows:
                row["entity_type"] = table.removeprefix("document_")
                out.append(row)
        return out[:limit]
