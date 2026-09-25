"""Transparent lexical + semantic hybrid retrieval."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional, Sequence

from backend.app.services.retriever import KeywordRetriever
from backend.app.services.vector_retriever import VectorRetriever


@dataclass(frozen=True)
class HybridResult:
    record: dict[str, Any]
    lexical_score: float
    vector_score: float
    metadata_score: float
    hybrid_score: float
    knowledge_id: str | None = None
    knowledge_type: str = "standard"
    source_id: str | None = None


class HybridRetriever:
    """Merge lexical and vector candidates with explicit configurable weights."""

    def __init__(
        self,
        lexical=None,
        vector=None,
        *,
        lexical_weight: float = 0.55,
        vector_weight: float = 0.35,
        metadata_weight: float = 0.10,
    ):
        total = lexical_weight + vector_weight + metadata_weight
        if total <= 0:
            raise ValueError("At least one hybrid weight must be positive.")
        self.lexical = lexical or KeywordRetriever()
        self.vector = vector or VectorRetriever()
        self.weights = {
            "lexical": lexical_weight / total,
            "vector": vector_weight / total,
            "metadata": metadata_weight / total,
        }

    @staticmethod
    def _version_score(record: dict[str, Any], query: str) -> float:
        # Current preference is permitted only when source data explicitly marks
        # the version verified. "Active" alone is not treated as current.
        score = 0.0
        if record.get("current_verified") is True:
            score += 8.0
        from backend.app.services.versioning import parse_version_reference
        requested = parse_version_reference(query)
        if requested:
            label, _ = requested
            if str(record.get("version_label") or record.get("number") or record.get("is_number") or "").strip().lower() == label.lower():
                score += 100.0
            else:
                score -= 100.0
        return score

    @staticmethod
    def _metadata_score(record: dict[str, Any]) -> float:
        status = str(record.get("knowledge_status") or "").lower()
        source = str(record.get("source") or "").strip()
        score = {
            "official_verified": 1.0,
            "demonstration_mock": 0.45,
            "application_generated": 0.25,
        }.get(status, 0.35)
        if source:
            score = min(1.0, score + 0.05)
        if str(record.get("status") or "").lower() == "active":
            score = min(1.0, score + 0.05)
        return score

    @staticmethod
    def _normalize_lexical(scores: list[float]) -> list[float]:
        if not scores:
            return []
        lo, hi = min(scores), max(scores)
        if hi <= lo:
            return [1.0 if hi > 0 else 0.0 for _ in scores]
        return [(s - lo) / (hi - lo) for s in scores]

    def search(
        self,
        query: str,
        *,
        category: Optional[str] = None,
        top_k: int = 10,
        lexical_limit: int | None = None,
        vector_limit: int | None = None,
        knowledge_types: Sequence[str] = ("standard", "faq", "service", "lab", "certification_step", "document"),
    ) -> list[HybridResult]:
        if top_k < 1:
            return []

        lexical_limit = lexical_limit or max(top_k * 4, 20)
        vector_limit = vector_limit or max(top_k * 4, 20)

        lexical_items = self.lexical.search(
            query, category=category, top_k=lexical_limit
        )
        lexical_raw = [float(item.score) for item in lexical_items]
        lexical_norm = self._normalize_lexical(lexical_raw)

        merged: dict[tuple[str, str], dict[str, Any]] = {}

        for item, normalized in zip(lexical_items, lexical_norm):
            record = dict(item.record)
            key = ("standard", str(record.get("number") or record.get("id") or ""))
            merged.setdefault(key, {
                "record": record,
                "lexical": 0.0,
                "vector": 0.0,
                "metadata": self._metadata_score(record),
                "knowledge_id": None,
                "knowledge_type": "standard",
                "source_id": record.get("number"),
            })
            merged[key]["lexical"] = max(merged[key]["lexical"], normalized)

        vector_items = self.vector.search(
            query,
            category=category,
            top_k=vector_limit,
            knowledge_types=knowledge_types,
        )
        for item in vector_items:
            record = dict(item.record)
            key = (item.knowledge_type, item.source_id)
            entry = merged.setdefault(key, {
                "record": record,
                "lexical": 0.0,
                "vector": 0.0,
                "metadata": self._metadata_score(record),
                "knowledge_id": item.knowledge_id,
                "knowledge_type": item.knowledge_type,
                "source_id": item.source_id,
            })
            # Prefer the richer vector metadata only when the lexical candidate
            # did not already supply a record.
            if not entry["record"] or len(record) > len(entry["record"]):
                entry["record"] = record
            entry["vector"] = max(entry["vector"], item.similarity)
            entry["metadata"] = self._metadata_score(entry["record"])
            entry["knowledge_id"] = entry["knowledge_id"] or item.knowledge_id

        results = []
        from backend.app.services.versioning import parse_version_reference
        requested_version = parse_version_reference(query)
        for entry in merged.values():
            version_bonus = self._version_score(entry["record"], query)
            # Explicit version references are hard constraints when a matching
            # version exists among candidates; otherwise the caller receives
            # only the available evidence rather than an invented version.
            if requested_version:
                label, _ = requested_version
                record_label = str(entry["record"].get("version_label") or entry["record"].get("number") or entry["record"].get("is_number") or "")
                if record_label.strip().lower() != label.lower():
                    continue
            score = (
                self.weights["lexical"] * entry["lexical"]
                + self.weights["vector"] * entry["vector"]
                + self.weights["metadata"] * entry["metadata"]
                + min(max(version_bonus, -100.0), 100.0) * 0.001
            )
            results.append(HybridResult(
                record=entry["record"],
                lexical_score=round(entry["lexical"], 6),
                vector_score=round(entry["vector"], 6),
                metadata_score=round(entry["metadata"], 6),
                hybrid_score=round(score, 6),
                knowledge_id=entry["knowledge_id"],
                knowledge_type=entry["knowledge_type"],
                source_id=entry["source_id"],
            ))

        current_request = bool(__import__("re").search(
            r"\b(current|latest|present|authoritative)\b", query or "", __import__("re").I
        ))
        results.sort(
            key=lambda item: (
                -(1 if current_request and item.record.get("current_verified") is True else 0),
                -item.hybrid_score,
                -item.vector_score,
                -item.lexical_score,
                str(item.record.get("number") or item.source_id or "")
            )
        )
        return results[:top_k]


def search_hybrid(
    query: str,
    *,
    category: Optional[str] = None,
    top_k: int = 10,
    knowledge_types: Sequence[str] = ("standard", "faq", "service", "lab", "certification_step", "document"),
) -> list[dict[str, Any]]:
    retriever = HybridRetriever(
        lexical_weight=settings_value("HYBRID_LEXICAL_WEIGHT"),
        vector_weight=settings_value("HYBRID_VECTOR_WEIGHT"),
        metadata_weight=settings_value("HYBRID_METADATA_WEIGHT"),
    )
    return [
        {
            **item.record,
            "relevance_score": item.hybrid_score,
            "version_context": item.record.get("version_context", {
                "version_id": item.record.get("version_id"),
                "version_label": item.record.get("version_label") or item.record.get("number") or item.record.get("is_number"),
                "publication_year": item.record.get("publication_year"),
                "version_kind": item.record.get("version_kind"),
                "current_verified": bool(item.record.get("current_verified", False)),
            }),
            "retrieval": {
                "lexical_score": item.lexical_score,
                "vector_score": item.vector_score,
                "hybrid_score": item.hybrid_score,
                "metadata_score": item.metadata_score,
                "knowledge_type": item.knowledge_type,
                "source_id": item.source_id,
            },
        }
        for item in retriever.search(
            query, category=category, top_k=top_k, knowledge_types=knowledge_types
        )
    ]


def settings_value(name: str) -> float:
    from backend.app.core.config import settings
    return float(getattr(settings, name))
