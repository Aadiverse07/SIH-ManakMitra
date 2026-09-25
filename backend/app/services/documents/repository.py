"""Supabase persistence for user-owned document intelligence records."""
from backend.app.database.client import supabase

class DocumentRepository:
    def _owned(self, user_id, document_id):
        result = supabase.table("documents").select("*").eq("id", document_id).eq("owner_user_id", user_id).limit(1).execute()
        rows = result.data or []
        return rows[0] if rows else None

    def create(self, data):
        return supabase.table("documents").insert(data).execute().data[0]

    def get(self, user_id, document_id):
        return self._owned(user_id, document_id)

    def list(self, user_id):
        return supabase.table("documents").select("*").eq("owner_user_id", user_id).order("created_at", desc=True).execute().data or []

    def duplicate(self, user_id, checksum):
        rows = supabase.table("documents").select("*").eq("owner_user_id", user_id).eq("checksum", checksum).limit(1).execute().data or []
        return rows[0] if rows else None

    def update(self, user_id, document_id, data):
        return supabase.table("documents").update(data).eq("id", document_id).eq("owner_user_id", user_id).execute().data[0]

    def delete(self, user_id, document_id):
        return supabase.table("documents").delete().eq("id", document_id).eq("owner_user_id", user_id).execute()

    def replace_children(self, document_id, pages, chunks, metadata):
        supabase.table("document_chunks").delete().eq("document_id", document_id).execute()
        supabase.table("document_pages").delete().eq("document_id", document_id).execute()
        supabase.table("document_metadata").delete().eq("document_id", document_id).execute()
        if pages:
            supabase.table("document_pages").insert(pages).execute()
        if chunks:
            supabase.table("document_chunks").insert(chunks).execute()
        if metadata:
            supabase.table("document_metadata").insert(metadata).execute()

    def clear_children(self, document_id):
        supabase.table("document_chunks").delete().eq("document_id", document_id).execute()
        supabase.table("document_pages").delete().eq("document_id", document_id).execute()
        supabase.table("document_metadata").delete().eq("document_id", document_id).execute()

    def insert_pages(self, rows):
        return supabase.table("document_pages").insert(rows).execute().data or []

    def insert_chunks(self, rows):
        if rows:
            supabase.table("document_chunks").insert(rows).execute()

    def insert_metadata(self, rows):
        if rows:
            supabase.table("document_metadata").insert(rows).execute()

    def get_version(self, document_id, checksum):
        rows = supabase.table("document_versions").select("*").eq("document_id", document_id).eq("checksum", checksum).limit(1).execute().data or []
        return rows[0] if rows else None

    def create_version(self, data):
        return supabase.table("document_versions").insert(data).execute().data[0]

    def pages(self, user_id, document_id):
        if not self.get(user_id, document_id):
            return []
        return supabase.table("document_pages").select("*").eq("document_id", document_id).order("page_number").execute().data or []

    def search(self, user_id, document_id, query, limit=20):
        if not self.get(user_id, document_id):
            return []
        q = f"%{query}%"
        return supabase.table("document_chunks").select("*").eq("document_id", document_id).ilike("content", q).order("chunk_index").limit(limit).execute().data or []
