"""Postgres/pgvector semantic retrieval."""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Optional, Sequence

from backend.app.database.client import supabase
from backend.app.services.embedding_service import EmbeddingError, get_embedding_service

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class VectorResult:
    record: dict[str, Any]
    similarity: float
    knowledge_id: str
    knowledge_type: str
    source_id: str
    content: str
    metadata: dict[str, Any]


class VectorRetriever:
    def __init__(self, embedding_service=None, db=None):
        self.embedding_service = embedding_service or get_embedding_service()
        self.db = db or supabase

    def search(
        self,
        query: str,
        *,
        category: Optional[str] = None,
        top_k: int = 10,
        knowledge_types: Sequence[str] = ("standard", "faq", "service", "lab", "certification_step", "document"),
        min_similarity: float = 0.0,
    ) -> list[VectorResult]:
        query = " ".join(str(query).split()).strip()
        if not query or top_k < 1 or not self.embedding_service.available:
            return []

        try:
            query_embedding = self.embedding_service.embed(query)
        except EmbeddingError as exc:
            logger.warning("phase10_vector_embedding_failed error=%s", type(exc).__name__)
            return []

        results: list[VectorResult] = []
        # One RPC per requested type keeps the SQL function simple and lets the
        # database use the vector index. The caller deduplicates the results.
        types = tuple(dict.fromkeys(knowledge_types))
        for knowledge_type in types:
            try:
                response = self.db.rpc(
                    "match_knowledge_chunks",
                    {
                        "query_embedding": "[" + ",".join(
                            format(float(v), ".10g") for v in query_embedding
                        ) + "]",
                        "match_count": top_k,
                        "filter_knowledge_type": knowledge_type,
                        "filter_category": category,
                        "filter_embedding_model": self.embedding_service.config.model,
                        "filter_embedding_dimensions": self.embedding_service.config.dimensions,
                        "min_similarity": max(0.0, min(1.0, min_similarity)),
                    },
                ).execute()
            except Exception as exc:
                logger.warning(
                    "phase10_vector_query_failed type=%s error=%s",
                    knowledge_type, type(exc).__name__,
                )
                continue

            for row in response.data or []:
                metadata = row.get("metadata") or {}
                record = metadata.get("record")
                if not isinstance(record, dict):
                    record = {
                        "content": row.get("content"),
                        "knowledge_type": row.get("knowledge_type"),
                        "knowledge_status": metadata.get("knowledge_status"),
                        "category": metadata.get("category"),
                        "source": metadata.get("source"),
                        "source_url": metadata.get("source_url"),
                    }
                results.append(VectorResult(
                    record=record,
                    similarity=max(0.0, min(1.0, float(row.get("similarity") or 0.0))),
                    knowledge_id=str(row.get("id")),
                    knowledge_type=str(row.get("knowledge_type") or knowledge_type),
                    source_id=str(row.get("source_id") or ""),
                    content=str(row.get("content") or ""),
                    metadata=metadata,
                ))

        # Keep the best vector hit for each source.
        best: dict[tuple[str, str], VectorResult] = {}
        for item in results:
            key = (item.knowledge_type, item.source_id)
            if key not in best or item.similarity > best[key].similarity:
                best[key] = item
        return sorted(
            best.values(),
            key=lambda item: (-item.similarity, item.source_id),
        )[:top_k]
