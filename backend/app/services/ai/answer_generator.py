"""Grounded answer generation for AI #1 with backend-owned provenance."""
from __future__ import annotations
from dataclasses import dataclass
import re
from typing import Any
from backend.app.services.ai.llm_service import LLMError, LLMQuotaError, get_llm_service
from backend.app.services.ai.prompts import build_grounded_prompt
from backend.app.services.provenance.models import Citation
from backend.app.services.provenance.service import build_citations, extract_citation_ids, validate_citations, format_citation_footer
from backend.app.services.language import LanguageInfo, localized_message, response_instruction

FALLBACK = "I couldn't find reliable BIS information for that question."

@dataclass(frozen=True)
class AIAnswer:
    answer: str
    grounding_status: str
    source_records: tuple[dict[str, Any], ...]
    fallback_required: bool
    provider_status: str = "not_called"
    citations: tuple[Citation, ...] = ()


def generate_grounded_answer(question: str, records: list[dict[str, Any]], *, llm_service=None, original_question: str | None = None, conversation_context: dict[str, Any] | None = None, language: LanguageInfo | None = None) -> AIAnswer:
    selected=tuple(records)
    citations=tuple(build_citations(list(selected)))
    language = language or LanguageInfo("en", "English")
    if not selected:
        return AIAnswer(localized_message("no_reliable_bis", language), "insufficient_context", selected, True, "not_called", ())
    prompt=build_grounded_prompt(
        question, list(selected), original_question=original_question,
        conversation_context=conversation_context,
        language_instruction=response_instruction(language),
    )
    service=llm_service or get_llm_service()
    try:
        answer=service.generate(prompt).strip()
        if not answer: raise LLMError("empty model answer")
        referenced=extract_citation_ids(answer)
        validation=validate_citations(list(citations), referenced)
        if referenced and not validation.valid:
            answer = re.sub(r"\[C\d+\]", "", answer).strip()
            grounding="citation_repaired"
        elif not referenced:
            grounding="retrieved_context_citations_backend_attached"
        else:
            grounding="retrieved_context_citations_validated"
        # The backend, not the model, owns the authoritative citation list.
        answer = answer + format_citation_footer(list(citations))
        return AIAnswer(answer, grounding, selected, False, "ok", citations)
    except LLMQuotaError:
        return AIAnswer(localized_message("ai1_unavailable", language), "retrieved_context", selected, True, "quota_exhausted", citations)
    except Exception:
        return AIAnswer(localized_message("ai1_unavailable", language), "retrieved_context", selected, True, "provider_error", citations)
