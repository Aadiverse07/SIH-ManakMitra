"""Build/update Phase 10 knowledge embeddings from existing BIS tables.

Run after migration 0006 and after the embedding provider is configured:
    python -m backend.scripts.index_embeddings

Only existing database content is indexed. This script does not invent BIS data.
"""
from __future__ import annotations

import hashlib
import logging
from typing import Any

from backend.app.core.config import settings
from backend.app.database.client import supabase
from backend.app.services.embedding_service import get_embedding_service

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


def _hash(content: str) -> str:
    material = f"{settings.EMBEDDING_MODEL}|{settings.EMBEDDING_DIMENSIONS}|{content}"
    return hashlib.sha256(material.encode("utf-8")).hexdigest()


def _standard(row: dict[str, Any]) -> dict[str, Any]:
    content = "\n".join(filter(None, [
        row.get("is_number"),
        row.get("title"),
        row.get("description"),
        f"Category: {row.get('category')}" if row.get("category") else None,
        f"Department: {row.get('dept')}" if row.get("dept") else None,
        f"Status: {row.get('status')}" if row.get("status") else None,
    ]))
    record = {
        "number": row.get("is_number"), "title": row.get("title"),
        "desc": row.get("description"), "category": row.get("category"),
        "dept": row.get("dept"), "status": row.get("status", "Active"),
        "reaffirmed": row.get("reaffirmed"), "language": row.get("language"),
        "superseded_by": row.get("superseded_by"),
        "knowledge_status": row.get("knowledge_status"),
        "source": row.get("source"), "source_url": row.get("source_url"),
        "source_updated_at": row.get("source_updated_at"),
        "created_at": row.get("created_at"), "updated_at": row.get("updated_at"),
    }
    return _chunk("standard", str(row["id"]), content, record)


def _service(row):
    content = "\n".join(filter(None, [row.get("name"), row.get("summary"), row.get("detail")]))
    record = {
        "number": None, "title": row.get("name"), "desc": row.get("summary") or row.get("detail"),
        "category": row.get("category"), "dept": None, "status": "Active",
        "knowledge_status": row.get("knowledge_status"), "source": row.get("source"),
        "source_url": row.get("source_url"),
    }
    return _chunk("service", str(row["id"]), content, record)


def _faq(row):
    content = f"Question: {row.get('question')}\nAnswer: {row.get('answer')}"
    record = {
        "number": None, "title": row.get("question"), "desc": row.get("answer"),
        "category": row.get("category"), "status": "Active",
        "knowledge_status": row.get("knowledge_status"), "source": row.get("source"),
        "source_url": row.get("source_url"),
    }
    return _chunk("faq", str(row["id"]), content, record)


def _lab(row):
    content = "\n".join(filter(None, [
        row.get("name"), row.get("city"), row.get("scope"), row.get("status")
    ]))
    record = {
        "number": None, "title": row.get("name"), "desc": row.get("scope"),
        "category": None, "status": row.get("status", "Recognised"),
        "knowledge_status": row.get("knowledge_status"), "source": row.get("source"),
        "source_url": row.get("source_url"),
    }
    return _chunk("lab", str(row["id"]), content, record)


def _cert_step(row):
    content = "\n".join(filter(None, [
        f"Step {row.get('step')}: {row.get('title')}",
        row.get("detail"),
    ]))
    record = {
        "number": None, "title": row.get("title"), "desc": row.get("detail"),
        "category": None, "status": "Active",
        "knowledge_status": row.get("knowledge_status"), "source": row.get("source"),
        "source_url": row.get("source_url"),
    }
    return _chunk("certification_step", str(row["id"]), content, record)



def _document(row):
    content = "\n".join(filter(None, [row.get("title"), row.get("content"), f"Category: {row.get('category')}" if row.get("category") else None]))
    record = {
        "number": None, "title": row.get("title"), "desc": row.get("content"),
        "category": row.get("category"), "status": "Active",
        "knowledge_status": row.get("knowledge_status"), "source": row.get("source"),
        "source_url": row.get("source_url"), "source_updated_at": row.get("source_updated_at"),
    }
    return _chunk("document", str(row["id"]), content, record)


def _chunk(kind: str, source_id: str, content: str, record: dict[str, Any]) -> dict[str, Any]:
    content = content.strip()
    return {
        "knowledge_type": kind,
        "source_id": source_id,
        "document_id": source_id,
        "content": content,
        "content_hash": _hash(content),
        "metadata": {
            "record": record,
            "category": record.get("category"),
            "knowledge_status": record.get("knowledge_status"),
            "source": record.get("source"),
            "source_url": record.get("source_url"),
            "embedding_model": settings.EMBEDDING_MODEL,
        },
    }


def load_rows(table: str) -> list[dict[str, Any]]:
    response = supabase.table(table).select("*").execute()
    return response.data or []


def run() -> dict[str, int]:
    service = get_embedding_service()
    if not service.available:
        raise RuntimeError(
            "Embedding provider is not configured. Set EMBEDDING_API_KEY and "
            "EMBEDDING_PROVIDER before indexing."
        )

    builders = [
        ("standards", _standard),
        ("services", _service),
        ("faqs", _faq),
        ("labs", _lab),
        ("cert_steps", _cert_step),
        ("knowledge_documents", _document),
    ]
    chunks: list[dict[str, Any]] = []
    for table, builder in builders:
        rows = load_rows(table)
        for row in rows:
            chunks.append(builder(row))

    embedded = 0
    batch_size = settings.EMBEDDING_BATCH_SIZE
    for start in range(0, len(chunks), batch_size):
        batch = chunks[start:start + batch_size]
        vectors = service.embed_batch([item["content"] for item in batch])
        payload = []
        for item, vector in zip(batch, vectors):
            payload.append({
                **item,
                "embedding": "[" + ",".join(format(float(v), ".10g") for v in vector) + "]",
                "embedding_model": settings.EMBEDDING_MODEL,
                "embedding_dimensions": settings.EMBEDDING_DIMENSIONS,
            })
        supabase.table("knowledge_chunks").upsert(
            payload,
            on_conflict="knowledge_type,source_id,content_hash,embedding_model,embedding_dimensions",
        ).execute()
        embedded += len(payload)
        logger.info("phase10_embeddings indexed=%d/%d", embedded, len(chunks))

    return {"chunks": len(chunks), "embedded": embedded}


if __name__ == "__main__":
    print(run())
