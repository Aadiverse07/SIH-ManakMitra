"""Phase 21 evidence-first retrieval orchestration.

The engine makes retrieval strategies explicit while preserving the existing
retrievers. It is deliberately deterministic and never fabricates evidence.
"""
from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any, Callable

from backend.app.services.retriever import KeywordRetriever
from backend.app.services.vector_retriever import VectorRetriever
from backend.app.services.documents.retriever import search_user_documents


def _key(record: dict[str, Any]) -> tuple[str, str]:
    return (
        str(record.get("knowledge_type") or record.get("entity_type") or "record"),
        str(record.get("knowledge_id") or record.get("id") or record.get("evidence_id") or record.get("number") or ""),
    )


def _add(target: dict[tuple[str, str], dict[str, Any]], records: list[dict[str, Any]], strategy: str) -> None:
    for record in records:
        item = dict(record)
        retrieval = dict(item.get("retrieval") or {})
        item.setdefault("retrieval_timestamp", datetime.now(timezone.utc).isoformat())
        retrieval.setdefault("strategy", strategy)
        item["retrieval"] = retrieval
        key = _key(item)
        if key == ("record", ""):
            key = (strategy, str(len(target)))
        existing = target.get(key)
        if existing is None or float(retrieval.get("hybrid_score", item.get("relevance_score", 0)) or 0) > float((existing.get("retrieval") or {}).get("hybrid_score", existing.get("relevance_score", 0)) or 0):
            target[key] = item


def _exact_public(query: str, limit: int) -> list[dict[str, Any]]:
    try:
        items = KeywordRetriever().search(query, top_k=limit)
        return [{**item.record, "relevance_score": item.score, "retrieval": {"strategy": "exact", "lexical_score": item.score, "hybrid_score": item.score}} for item in items if item.score > 0]
    except Exception:
        return []


def _semantic_public(query: str, limit: int) -> list[dict[str, Any]]:
    try:
        items = VectorRetriever().search(query, top_k=limit)
        return [{**item.record, "relevance_score": item.similarity, "retrieval": {"strategy": "semantic", "vector_score": item.similarity, "hybrid_score": item.similarity}} for item in items]
    except Exception:
        return []


def _metadata_queries(query: str) -> list[str]:
    queries = []
    standards = re.findall(r"\bIS\s*\d{1,6}(?::\d{4})?(?:\s*[/&-]\s*\d{1,6})?\b", query, re.I)
    clauses = re.findall(r"\b(?:clause|section)\s+[0-9]+(?:\.[0-9]+)*\b", query, re.I)
    queries.extend(standards)
    queries.extend(clauses)
    return list(dict.fromkeys(queries))


def retrieve_evidence(
    query: str,
    *,
    base_retrieval: Callable[..., list[dict[str, Any]]],
    category: str | None = None,
    top_k: int = 8,
    user_id: str | None = None,
) -> list[dict[str, Any]]:
    """Run explicit retrieval layers before the answer generator.

    The supplied base retriever remains the primary hybrid/semantic path. The
    extra layers are additive and fail closed if a database/index is unavailable.
    """
    merged: dict[tuple[str, str], dict[str, Any]] = {}

    try:
        _add(merged, list(base_retrieval(query, category=category, top_k=max(top_k, 8))), "hybrid")
    except Exception:
        pass

    # 1. Exact retrieval
    _add(merged, _exact_public(query, max(top_k, 6)), "exact")

    # 2. Keyword retrieval
    try:
        keyword = KeywordRetriever().search(query, category=category, top_k=max(top_k, 8))
        _add(merged, [{**x.record, "relevance_score": x.score, "retrieval": {"strategy": "keyword", "lexical_score": x.score, "hybrid_score": x.score}} for x in keyword], "keyword")
    except Exception:
        pass

    # 3. Semantic retrieval
    _add(merged, _semantic_public(query, max(top_k, 8)), "semantic")

    # 4. Metadata retrieval (standard number / clause / section)
    for metadata_query in _metadata_queries(query):
        try:
            _add(merged, _exact_public(metadata_query, max(top_k, 6)), "metadata")
        except Exception:
            pass

    # 5. Related-standard retrieval: use only identifiers/titles already
    # retrieved; never synthesize a standard number.
    seeds = list(merged.values())[:3]
    for seed in seeds:
        number = seed.get("number") or seed.get("is_number")
        title = seed.get("title")
        if not number and not title:
            continue
        related_query = str(number or title)
        try:
            _add(merged, _exact_public(related_query, 3), "related-standard")
        except Exception:
            pass

    # 6. Private document retrieval, always scoped by authenticated user ID.
    if user_id:
        try:
            _add(merged, search_user_documents(user_id, query, top_k=max(top_k, 8)), "document")
        except Exception:
            pass

    records = list(merged.values())
    records.sort(key=lambda r: -float((r.get("retrieval") or {}).get("hybrid_score", r.get("relevance_score", 0)) or 0))
    return records[:top_k]
