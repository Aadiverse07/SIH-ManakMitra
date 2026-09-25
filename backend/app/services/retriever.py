"""Phase 5 BIS retrieval layer.

The retriever is deliberately separate from the LLM.  It retrieves only records
that already exist in the BIS knowledge database and ranks those records locally.
A future semantic/vector retriever can implement the same interface without
changing the API or AI layer.
"""
from __future__ import annotations

import re
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Optional

from backend.app.database.client import supabase
from backend.app.services.data_service import row_to_standard


TOP_K = 10
CANDIDATE_LIMIT = 100

# Common words that add little value to BIS catalogue search.
_STOPWORDS = {
    "a", "an", "and", "are", "for", "from", "in", "is", "of", "on", "or",
    "the", "to", "with", "standard", "standards", "code", "codes",
}


def _norm(value: str) -> str:
    return re.sub(r"\s+", " ", value.strip().lower())


def _tokens(query: str) -> list[str]:
    # Keep useful terms such as "456", "structural", "concrete".
    raw = re.findall(r"[a-z0-9]+", query.lower())
    return [t for t in raw if t not in _STOPWORDS and len(t) > 1]


def _standard_number_query(query: str) -> Optional[str]:
    """Return an IS-number prefix when the query looks like 'IS 456'."""
    m = re.fullmatch(r"\s*(?:is\s*)?(\d{1,6})\s*(?::\s*(\d{4}))?\s*", query, re.I)
    if not m:
        return None
    return f"IS {m.group(1)}" + (f":{m.group(2)}" if m.group(2) else "")


@dataclass(frozen=True)
class RetrievalResult:
    record: dict[str, Any]
    score: float


class Retriever(ABC):
    @abstractmethod
    def search(
        self, query: str, *, category: Optional[str] = None, top_k: int = TOP_K
    ) -> list[RetrievalResult]:
        raise NotImplementedError


class KeywordRetriever(Retriever):
    """Postgres-backed lexical candidate retrieval + deterministic ranking."""

    def _candidates(self, query: str, category: Optional[str]) -> list[dict[str, Any]]:
        db = supabase.table("standards").select("*")

        if category:
            db = db.eq("category", category)

        terms = _tokens(query)
        number_query = _standard_number_query(query)

        # Exact/prefix standard-number lookup gets a targeted DB condition.
        # For ordinary text, search each meaningful token across the indexed
        # catalogue fields. The application then performs the final ranking.
        if number_query:
            like = f"%{number_query}%"
            expression = (
                f"is_number.ilike.{like},"
                f"title.ilike.{like},"
                f"description.ilike.{like}"
            )
            db = db.or_(expression)
        elif terms:
            clauses = []
            for term in terms[:8]:
                like = f"%{term}%"
                clauses.extend([
                    f"is_number.ilike.{like}",
                    f"title.ilike.{like}",
                    f"description.ilike.{like}",
                    f"category.ilike.{like}",
                    f"dept.ilike.{like}",
                ])
            db = db.or_(",".join(clauses))
        else:
            # Empty/stop-word-only search is intentionally bounded.
            pass

        response = db.limit(CANDIDATE_LIMIT).execute()
        return response.data or []

    @staticmethod
    def _score(row: dict[str, Any], query: str, category: Optional[str]) -> float:
        q = _norm(query)
        number = _norm(row.get("is_number", ""))
        title = _norm(row.get("title", ""))
        desc = _norm(row.get("description", ""))
        row_category = _norm(row.get("category", ""))
        dept = _norm(row.get("dept", ""))

        score = 0.0
        number_q = _standard_number_query(query)
        terms = _tokens(query)

        # Highest priority: standard-number lookup.
        if number_q:
            nq = _norm(number_q)
            if number == nq:
                score += 1000
            elif number.startswith(nq + ":") or number.startswith(nq + " "):
                score += 850
            elif nq in number:
                score += 650

        # Strong title/phrase matches.
        if q and q in title:
            score += 350
        if q and q in desc:
            score += 90

        # Token-level ranking. Title > description > number > category.
        for term in terms:
            if term in title:
                score += 90
                # A token at a word boundary is stronger than a substring.
                if re.search(rf"\b{re.escape(term)}\b", title):
                    score += 25
            if term in desc:
                score += 35
            if term in number:
                score += 55
            if term in row_category:
                score += 25
            if term in dept:
                score += 10

        # Category filter is a constraint; when explicitly requested it also
        # gives a small ranking boost, but never invents a match.
        if category and row_category == _norm(category):
            score += 30

        # Prefer active knowledge records only when otherwise tied; this does
        # not hide superseded records that genuinely match the query.
        if str(row.get("status", "")).lower() == "active":
            score += 2

        return score

    def search(
        self, query: str, *, category: Optional[str] = None, top_k: int = TOP_K
    ) -> list[RetrievalResult]:
        query = query.strip()
        if top_k < 1:
            return []

        rows = self._candidates(query, category)
        ranked = [
            RetrievalResult(record=r, score=self._score(r, query, category))
            for r in rows
        ]

        # Do not return DB rows that have zero lexical relevance for a query.
        if query:
            ranked = [x for x in ranked if x.score > 0]

        ranked.sort(
            key=lambda x: (-x.score, _norm(x.record.get("is_number", "")))
        )
        return ranked[:top_k]


def search_bis(
    query: str, *, category: Optional[str] = None, top_k: int = TOP_K
) -> list[dict[str, Any]]:
    """Public retrieval function used by the HTTP layer and future AI layer."""
    retriever = KeywordRetriever()
    return [
        {
            **row_to_standard(item.record),
            "relevance_score": round(item.score, 2),
        }
        for item in retriever.search(query, category=category, top_k=top_k)
    ]
