"""Evidence-backed BIS Standards Knowledge Graph.

This service never invents relationships. It can materialize:
1) existing Phase 13 standard lifecycle relationships;
2) explicit standard references found in user-owned processed documents when
   the referenced standard/version can be resolved exactly;
3) explicitly supplied verified project relationships.
"""
from __future__ import annotations

import re
from typing import Any
from backend.app.database.client import supabase

STANDARD_REF_RE = re.compile(r"\bIS\s*([0-9]{1,6}(?:\s*\([^)]*\))?)\s*:\s*(\d{4})\b", re.I)
RELATION_PATTERNS = (
    ("TESTED_BY", re.compile(r"(?:tested|test(?:ing)?|determined)\s+(?:in accordance with|by|using)\s+(IS\s*[0-9]{1,6}(?:\s*\([^)]*\))?\s*:\s*\d{4})", re.I)),
    ("REFERENCES", re.compile(r"(?:reference(?:s|d)?|as per|in accordance with|according to)\s+(IS\s*[0-9]{1,6}(?:\s*\([^)]*\))?\s*:\s*\d{4})", re.I)),
    ("REQUIRES", re.compile(r"(?:requires?|shall comply with)\s+(IS\s*[0-9]{1,6}(?:\s*\([^)]*\))?\s*:\s*\d{4})", re.I)),
)

ALLOWED_TYPES = {"STANDARD", "DOCUMENT", "CLAUSE", "AMENDMENT", "REVISION", "PRODUCT", "MATERIAL", "TESTING_METHOD", "CERTIFICATION_SCHEME", "LABORATORY", "SERVICE"}
ALLOWED_RELATIONS = {"REFERENCES", "RELATED_TO", "AMENDS", "SUPERSEDES", "SUPERSEDED_BY", "TESTED_BY", "USED_WITH", "REQUIRES", "APPLIES_TO"}


def _norm_standard(value: str) -> str:
    return re.sub(r"\s+", " ", value or "").strip().upper()


def _node_key(entity_type: str, label: str, ref_id: str | None = None) -> str:
    base = _norm_standard(label) if entity_type in {"STANDARD", "TESTING_METHOD", "PRODUCT", "MATERIAL"} else re.sub(r"\s+", " ", label or "").strip().lower()
    return f"{entity_type}:{base}:{ref_id or ''}"


def _first(rows: list[dict[str, Any]]) -> dict[str, Any] | None:
    return rows[0] if rows else None


class BISGraphService:
    def _get_node_by_key(self, key: str):
        rows = supabase.table("bis_graph_nodes").select("*").eq("canonical_key", key).limit(1).execute().data or []
        return _first(rows)

    def _upsert_node(self, data: dict[str, Any]) -> dict[str, Any]:
        if data["entity_type"] not in ALLOWED_TYPES:
            raise ValueError("unsupported graph entity type")
        existing = self._get_node_by_key(data["canonical_key"])
        if existing:
            return existing
        return supabase.table("bis_graph_nodes").insert(data).execute().data[0]

    def _upsert_edge(self, data: dict[str, Any]) -> dict[str, Any]:
        if data["relationship_type"] not in ALLOWED_RELATIONS:
            raise ValueError("unsupported graph relationship")
        existing = (supabase.table("bis_graph_edges").select("*")
                    .eq("from_node_id", data["from_node_id"])
                    .eq("to_node_id", data["to_node_id"])
                    .eq("relationship_type", data["relationship_type"])
                    .eq("source_record_id", data.get("source_record_id") or "")
                    .limit(1).execute().data or [])
        if existing:
            return existing[0]
        return supabase.table("bis_graph_edges").insert(data).execute().data[0]

    def ensure_standard_node(self, version: dict[str, Any]) -> dict[str, Any]:
        label = version.get("version_label") or version.get("is_number") or ""
        return self._upsert_node({
            "entity_type": "STANDARD",
            "label": label,
            "canonical_key": _node_key("STANDARD", label, str(version.get("id"))),
            "standard_version_id": version.get("id"),
            "metadata": {"publication_year": version.get("publication_year"), "version_kind": version.get("version_kind")},
            "source_kind": "OFFICIAL_METADATA",
            "source_url": version.get("source_url"),
            "source_record_id": str(version.get("id")),
            "is_inferred": False,
        })

    def sync_official_standard_relationships(self, standard_number: str | None = None) -> int:
        q = supabase.table("standard_relationships").select("*")
        rows = q.execute().data or []
        count = 0
        for rel in rows:
            from_versions = supabase.table("standard_versions").select("*").eq("id", rel["from_version_id"]).limit(1).execute().data or []
            to_versions = supabase.table("standard_versions").select("*").eq("id", rel["to_version_id"]).limit(1).execute().data or []
            fv, tv = _first(from_versions), _first(to_versions)
            if not fv or not tv:
                continue
            if standard_number and _norm_standard(standard_number) not in {_norm_standard(str(fv.get("version_label"))), _norm_standard(str(tv.get("version_label")))}:
                continue
            # Phase 13's standard_relationships allows a broader legacy vocabulary
            # (e.g. 'amended_by', 'reaffirms', 'withdrawn', 'replaced_by') than the
            # Phase 22 graph relationship set. Skip anything outside the graph's
            # declared vocabulary rather than raising, so one legacy row can't
            # take down the whole standards graph endpoint.
            if str(rel["relationship_type"]).upper() not in ALLOWED_RELATIONS:
                continue
            fn = self.ensure_standard_node(fv); tn = self.ensure_standard_node(tv)
            edge = self._upsert_edge({
                "from_node_id": fn["id"], "to_node_id": tn["id"],
                "relationship_type": str(rel["relationship_type"]).upper(),
                "source_kind": "OFFICIAL_METADATA",
                "source_record_id": str(rel.get("id")),
                "source_url": rel.get("source_url"),
                "evidence_text": rel.get("evidence_note"),
                "is_inferred": False,
                "verified": True,
            })
            count += bool(edge)
        return count

    def sync_document_references(self, user_id: str, document_id: str) -> int:
        docs = supabase.table("documents").select("*").eq("id", document_id).eq("owner_user_id", user_id).limit(1).execute().data or []
        doc = _first(docs)
        if not doc:
            raise LookupError("Document not found")
        if doc.get("processing_status") != "processed":
            return 0
        version_rows = supabase.table("document_versions").select("*").eq("document_id", document_id).eq("id", doc.get("version_id")).limit(1).execute().data or []
        version = _first(version_rows)
        if not version:
            return 0
        source_label = doc.get("title") or doc.get("original_filename") or document_id
        doc_node = self._upsert_node({
            "entity_type": "DOCUMENT", "label": source_label,
            "canonical_key": _node_key("DOCUMENT", source_label, document_id),
            "document_id": document_id, "owner_user_id": user_id,
            "metadata": {"standard_number": doc.get("standard_number"), "document_version": doc.get("document_version")},
            "source_kind": "DOCUMENT_REFERENCE", "source_url": doc.get("source_url"),
            "source_record_id": document_id, "is_inferred": False,
        })
        pages = supabase.table("document_pages").select("*").eq("document_id", document_id).order("page_number").execute().data or []
        created = 0
        for page in pages:
            text = page.get("text_content") or ""
            matches = []
            for relation_type, pattern in RELATION_PATTERNS:
                matches.extend((relation_type, m.group(1)) for m in pattern.finditer(text))
            if not matches:
                # A bare reference is still an explicit REFERENCES relationship.
                matches.extend(("REFERENCES", m.group(0)) for m in STANDARD_REF_RE.finditer(text))
            for relation_type, ref in matches:
                target_label = _norm_standard(ref)
                sv_rows = supabase.table("standard_versions").select("*").eq("version_label", target_label).limit(2).execute().data or []
                if len(sv_rows) != 1:
                    # Ambiguous/unresolved references are deliberately not put in the graph.
                    continue
                target = self.ensure_standard_node(sv_rows[0])
                evidence = text[:2000]
                self._upsert_edge({
                    "from_node_id": doc_node["id"], "to_node_id": target["id"],
                    "relationship_type": relation_type, "source_kind": "DOCUMENT_REFERENCE",
                    "source_record_id": f"{document_id}:page:{page.get('page_number')}:{target_label}:{relation_type}",
                    "source_document_id": document_id, "source_url": doc.get("source_url"),
                    "evidence_text": evidence, "is_inferred": False, "verified": True,
                    "metadata": {"page_number": page.get("page_number"), "clause": page.get("clause")},
                })
                created += 1
        return created

    def query_standard(self, standard_number: str, relationship_type: str | None = None, limit: int = 50) -> dict[str, Any]:
        # Materialize only authoritative Phase 13 relationships.
        self.sync_official_standard_relationships(standard_number)
        q = _norm_standard(standard_number)
        versions = supabase.table("standard_versions").select("*").eq("version_label", q).limit(20).execute().data or []
        nodes = []
        edges = []
        for v in versions:
            node = self._get_node_by_key(_node_key("STANDARD", v.get("version_label") or "", str(v.get("id"))))
            if not node:
                node = self.ensure_standard_node(v)
            nodes.append(node)
            eq = supabase.table("bis_graph_edges").select("*").or_(f"from_node_id.eq.{node['id']},to_node_id.eq.{node['id']}").limit(limit).execute().data or []
            if relationship_type:
                eq = [e for e in eq if e.get("relationship_type") == relationship_type.upper()]
            # A public standard graph must never expose a private document node.
            # The backend uses a service-role client, so enforce this boundary in
            # application code in addition to database RLS.
            public_edges = []
            for edge in eq:
                endpoint_ids = {edge.get("from_node_id"), edge.get("to_node_id")} - {node["id"]}
                safe = True
                for endpoint_id in endpoint_ids:
                    endpoint = supabase.table("bis_graph_nodes").select("owner_user_id").eq("id", endpoint_id).limit(1).execute().data or []
                    if endpoint and endpoint[0].get("owner_user_id") is not None:
                        safe = False
                        break
                if safe:
                    public_edges.append(edge)
            edges.extend(public_edges)
        return self._expand(nodes, edges, limit)

    def query_document(self, user_id: str, document_id: str, limit: int = 50) -> dict[str, Any]:
        owned = supabase.table("documents").select("id").eq("id", document_id).eq("owner_user_id", user_id).limit(1).execute().data or []
        if not owned:
            raise LookupError("Document not found")
        self.sync_document_references(user_id, document_id)
        nodes = supabase.table("bis_graph_nodes").select("*").eq("document_id", document_id).limit(20).execute().data or []
        ids = [n["id"] for n in nodes]
        if not ids:
            return {"nodes": [], "edges": []}
        # Include both outgoing and incoming edges so the graph can answer
        # questions such as which standards reference a document, when such a
        # verified edge actually exists.
        outgoing = supabase.table("bis_graph_edges").select("*").in_("from_node_id", ids).limit(limit).execute().data or []
        incoming = supabase.table("bis_graph_edges").select("*").in_("to_node_id", ids).limit(limit).execute().data or []
        seen = {(e.get("id") or (e.get("from_node_id"), e.get("to_node_id"), e.get("relationship_type"))) for e in outgoing}
        edges = outgoing + [e for e in incoming if (e.get("id") or (e.get("from_node_id"), e.get("to_node_id"), e.get("relationship_type"))) not in seen]
        return self._expand(nodes, edges, limit)

    def _expand(self, nodes: list[dict[str, Any]], edges: list[dict[str, Any]], limit: int) -> dict[str, Any]:
        node_map = {n["id"]: n for n in nodes}
        for edge in edges[:limit]:
            for node_id in (edge.get("from_node_id"), edge.get("to_node_id")):
                if node_id in node_map:
                    continue
                rows = supabase.table("bis_graph_nodes").select("*").eq("id", node_id).limit(1).execute().data or []
                if rows:
                    node_map[node_id] = rows[0]
        return {"nodes": list(node_map.values()), "edges": edges[:limit]}
