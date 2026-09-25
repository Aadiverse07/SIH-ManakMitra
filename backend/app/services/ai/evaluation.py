"""Structured, deterministic evaluation of AI #1 results.

The evaluator never asks another model to judge AI #1. It validates the shape and
basic grounding/completeness signals locally so the fallback decision is
predictable and cheap.
"""
from __future__ import annotations

import re
from typing import Any

from pydantic import BaseModel, Field


FALLBACK_TEXT = "I couldn't find reliable BIS information for that question."

# The grounding_status values that answer_generator.py actually returns when
# AI #1 successfully produced an answer backed by retrieved BIS records. Note
# that the bare "retrieved_context" string is only emitted by answer_generator
# on provider failure (quota/error), where provider_ok is already False, so it
# must not be treated as a successful-grounding signal here.
GROUNDED_STATUSES = {
    "retrieved_context_citations_backend_attached",
    "retrieved_context_citations_validated",
    "citation_repaired",
}

class AI1Evaluation(BaseModel):
    answer: str
    understood: bool
    sufficient_context: bool
    grounded: bool
    complete_enough: bool
    confidence: float = Field(ge=0.0, le=1.0)
    reason: str


def _record_terms(records: list[dict[str, Any]]) -> set[str]:
    terms: set[str] = set()
    for record in records:
        for key in ("number", "title"):
            value = str(record.get(key) or "").lower()
            for token in re.findall(r"[a-z0-9]+", value):
                if len(token) >= 3:
                    terms.add(token)
    return terms


def evaluate_ai1(
    question: str,
    answer: str,
    records: list[dict[str, Any]],
    *,
    provider_ok: bool,
    grounding_status: str,
) -> AI1Evaluation:
    """Return a typed AI #1 evaluation without a second LLM call."""
    q = question.strip()
    a = (answer or "").strip()
    sufficient_context = bool(records)

    if not a or not q:
        return AI1Evaluation(
            answer=a or FALLBACK_TEXT,
            understood=False,
            sufficient_context=sufficient_context,
            grounded=False,
            complete_enough=False,
            confidence=0.0,
            reason="Missing question or answer.",
        )

    if a == FALLBACK_TEXT:
        return AI1Evaluation(
            answer=a,
            understood=True,
            sufficient_context=sufficient_context,
            grounded=False,
            complete_enough=False,
            confidence=0.0,
            reason="AI #1 returned the safe information-not-found fallback.",
        )

    # AI #1 is considered grounded only when the generator reports retrieved
    # context and the response contains at least one identifying fact from the
    # selected records. This is deliberately conservative.
    terms = _record_terms(records)
    answer_terms = set(re.findall(r"[a-z0-9]+", a.lower()))
    grounded = bool(provider_ok and sufficient_context and grounding_status in GROUNDED_STATUSES)
    if grounded and terms:
        grounded = bool(answer_terms & terms)

    complete_enough = len(a) >= 20 and not a.endswith(("...", "…"))
    understood = bool(q and provider_ok)

    score = 0.0
    score += 0.25 if understood else 0
    score += 0.25 if sufficient_context else 0
    score += 0.30 if grounded else 0
    score += 0.20 if complete_enough else 0
    confidence = round(min(1.0, score), 2)

    reasons = []
    if not understood:
        reasons.append("question/answer understanding could not be established")
    if not sufficient_context:
        reasons.append("retrieval returned no context")
    if not grounded:
        reasons.append("answer failed the local grounding checks")
    if not complete_enough:
        reasons.append("answer appears incomplete")
    reason = "; ".join(reasons) if reasons else "AI #1 passed the local evaluation."

    return AI1Evaluation(
        answer=a,
        understood=understood,
        sufficient_context=sufficient_context,
        grounded=grounded,
        complete_enough=complete_enough,
        confidence=confidence,
        reason=reason,
    )
