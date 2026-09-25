"""Phase 7 request pipeline: FAQ/cache -> AI #1 -> conditional AI #2 fallback."""
from __future__ import annotations

import logging
import inspect
import time
from dataclasses import dataclass
from typing import Any

from backend.app.services.ai.answer_generator import AIAnswer, generate_grounded_answer
from backend.app.services.moderation import moderation_guard
from backend.app.services.ai.evaluation import AI1Evaluation, evaluate_ai1
from backend.app.services.ai.fallback import AI2Fallback, AI2Result
from backend.app.services.cache.service import CacheService
from backend.app.services.faq.service import FAQMatcher, normalize_question
from backend.app.services.hybrid_retriever import search_hybrid
from backend.app.core.config import settings
from backend.app.core.usage import metrics
from backend.app.services.provenance.service import build_citations, format_citation_footer
from backend.app.services.provenance.models import Citation
from backend.app.services.context.service import ConversationContext, rewrite_query
from backend.app.services.versioning import constrain_records_to_version
from backend.app.services.language import detect_language, language_from_locale, localized_message
from backend.app.services.documents.retriever import search_user_documents
from backend.app.services.provenance.evidence_engine import retrieve_evidence
from backend.app.services.provenance.grounding import (
    DIRECT_EVIDENCE, DERIVED_FROM_EVIDENCE, PARTIAL_EVIDENCE,
    INSUFFICIENT_EVIDENCE, FALLBACK, validate_grounding,
)

logger = logging.getLogger(__name__)
AI1_CONFIDENCE_THRESHOLD = 0.75


@dataclass(frozen=True)
class AI1PipelineResult:
    reply: str
    source: str
    confidence: float | None
    grounding_status: str
    source_records: tuple[dict[str, Any], ...]
    fallback_required: bool
    provider_status: str
    ai1_evaluation: AI1Evaluation | None = None
    ai2_used: bool = False
    execution_ms: int = 0
    citations: tuple[Citation, ...] = ()
    resolved_query: str | None = None
    context_used: bool = False


class AI1Pipeline:
    """Coordinates retrieval, AI #1 evaluation, and conditional AI #2 fallback."""

    def __init__(
        self,
        faq_matcher: FAQMatcher,
        cache: CacheService,
        retrieval=search_hybrid,
        answer_generator=generate_grounded_answer,
        ai2_fallback: AI2Fallback | None = None,
        cache_ttl_seconds: int = 3600,
        top_k: int = 6,
        ai1_confidence_threshold: float = AI1_CONFIDENCE_THRESHOLD,
    ):
        self.faq_matcher = faq_matcher
        self.cache = cache
        self.retrieval = retrieval
        self.answer_generator = answer_generator
        self.ai2_fallback = ai2_fallback or AI2Fallback()
        self.cache_ttl_seconds = cache_ttl_seconds
        self.top_k = top_k
        self.ai1_confidence_threshold = ai1_confidence_threshold

    def _fallback_needed(self, evaluation: AI1Evaluation) -> bool:
        return not (
            evaluation.understood
            and evaluation.sufficient_context
            and evaluation.grounded
            and evaluation.complete_enough
            and evaluation.confidence >= self.ai1_confidence_threshold
        )

    def answer(
        self, question: str, category: str | None = None, *,
        conversation_context: ConversationContext | None = None,
        language_code: str | None = None,
        user_id: str | None = None,
    ) -> AI1PipelineResult:
        started = time.perf_counter()
        language = language_from_locale(language_code) if language_code else None
        language = language or detect_language(question)
        normalized = normalize_question(question)
        original_question = normalized
        normalized, context_used = rewrite_query(normalized, conversation_context) if conversation_context else (normalized, False)
        # The rewritten query is only surfaced when context actually changed it,
        # so callers can distinguish "resolved from context" from "asked as-is".
        resolved_query = normalized if context_used else None
        if not normalized:
            return AI1PipelineResult(
                reply=localized_message("empty", language),
                source="validation",
                confidence=None,
                grounding_status="not_applicable",
                source_records=(),
                fallback_required=False,
                provider_status="not_called",
                resolved_query=resolved_query,
                context_used=context_used,
            )

        # Sexual/harm-related content is refused before any retrieval, cache,
        # or AI #1/#2 call -- this is a pure short-circuit and never changes
        # behavior for a clean query. See services/moderation.py.
        moderation = moderation_guard.check(user_id or "anonymous", normalized)
        if moderation.flagged:
            return AI1PipelineResult(
                reply=moderation.message,
                source="moderation_blocked" if moderation.blocked else "moderation_warning",
                confidence=None,
                grounding_status="moderation_blocked" if moderation.blocked else "moderation_warning",
                source_records=(),
                fallback_required=False,
                provider_status="not_called",
                resolved_query=resolved_query,
                context_used=context_used,
            )

        # Trusted FAQ is a deterministic successful path. No AI #1 or AI #2.
        match = self.faq_matcher.match(normalized, category=category)
        if match:
            key = CacheService.make_key("faq", normalized)
            cached = self.cache.get(key)
            if cached is not None:
                metrics.increment("cache_hits")
                return AI1PipelineResult(
                    cached, "cache", match.confidence, "faq", (), False, "not_called",
                    resolved_query=resolved_query, context_used=context_used,
                )
            metrics.increment("faq_hits")
            self.cache.set(key, match.answer, self.cache_ttl_seconds)
            return AI1PipelineResult(
                match.answer, "faq", match.confidence, "faq", (), False, "not_called",
                resolved_query=resolved_query, context_used=context_used,
            )

        context_namespace = (
            f"{normalized}|ctx:{conversation_context.conversation_id if conversation_context else 'anonymous'}"
            f"|refs:{','.join(conversation_context.referenced_standards) if conversation_context else ''}"
            f"|user:{user_id or 'anonymous'}"
        )
        # Phase 21 evidence/citation semantics changed the cached response
        # contract; version the namespace so stale Phase 20 fallback answers do
        # not survive after deployment.
        query_key = CacheService.make_key("query", f"evidence:v21|{context_namespace}")
        cached = self.cache.get(query_key)
        if cached is not None:
            metrics.increment("cache_hits")
            if isinstance(cached, dict):
                cached_citations = tuple(Citation.model_validate(c) for c in cached.get("citations", []))
                return AI1PipelineResult(
                    str(cached.get("reply", "")), "cache", cached.get("confidence"),
                    str(cached.get("grounding_status", "cached_final")), (), False,
                    "not_called", citations=cached_citations, resolved_query=resolved_query,
                    context_used=context_used,
                )
            # Backward compatibility with pre-Phase-12 cache entries.
            return AI1PipelineResult(
                cached, "cache", None, "cached_final", (), False, "not_called",
                resolved_query=resolved_query, context_used=context_used,
            )

        retrieval_kwargs = {"category": category, "top_k": self.top_k}
        try:
            if "user_id" in inspect.signature(self.retrieval).parameters:
                retrieval_kwargs["user_id"] = user_id
        except (TypeError, ValueError):
            pass

        # Phase 21 makes retrieval layers explicit. Custom injected retrievers
        # used by tests/integrations remain untouched; the production hybrid
        # retriever gets the full evidence cascade.
        if self.retrieval is search_hybrid:
            records = retrieve_evidence(
                normalized,
                base_retrieval=self.retrieval,
                category=category,
                top_k=max(self.top_k, 8),
                user_id=user_id,
            )
        else:
            records = self.retrieval(normalized, **retrieval_kwargs)
            if user_id:
                try:
                    private_records = search_user_documents(user_id, normalized, top_k=self.top_k)
                except Exception as exc:
                    logger.warning("phase20_private_document_retrieval_skipped error=%s", exc)
                    private_records = []
                records = tuple(private_records) + tuple(records) if private_records else tuple(records)
        # Version safety must prevent incompatible versions from being merged,
        # but an unresolved version query must NOT erase all evidence.  The
        # previous behavior returned an empty list whenever retrieval produced
        # multiple version labels without an authoritative current-version
        # marker.  That made AI #1 report ``provider=not_called`` and forced
        # every such request into AI #2, even though usable BIS evidence had
        # already been retrieved.  Preserve the candidates and let AI #1 state
        # the version ambiguity explicitly (the grounded system prompt already
        # forbids merging incompatible versions). Exact/authoritatively resolved
        # version requests still use the strict constraint above.
        retrieved_records = tuple(records)
        records, version_resolution = constrain_records_to_version(records, normalized)
        if (
            not records
            and retrieved_records
            and version_resolution.reason
            in {
                "multiple_versions_without_authoritative_resolution",
                "historical_request_requires_verified_version",
            }
        ):
            records = list(retrieved_records)
            logger.info(
                "phase13_version_ambiguity_preserved candidates=%d reason=%s",
                len(records),
                version_resolution.reason,
            )
        records = tuple(records[:max(self.top_k, 8)])
        if records:
            metrics.increment("bis_retrieval_hits")

        # Hard per-request AI budget: exactly one AI #1 attempt and at most one
        # conditional AI #2 attempt. No recursive pipeline calls are possible.
        if settings.MAX_AI1_CALLS_PER_REQUEST < 1:
            return AI1PipelineResult(
                "I couldn't generate an AI answer right now. BIS search is still available.",
                "ai_disabled", None, "retrieved_context" if records else "insufficient_context",
                tuple(records), False, "not_called", resolved_query=resolved_query,
                context_used=context_used,
            )

        ai_started = time.perf_counter()
        metrics.increment("ai1_calls")
        ai1: AIAnswer = self.answer_generator(
            normalized, records, original_question=original_question,
            conversation_context=({"recent_messages":[dict(m) for m in conversation_context.recent_messages],"referenced_standards":list(conversation_context.referenced_standards),"referenced_clauses":list(conversation_context.referenced_clauses),"active_topic":conversation_context.active_topic,"summary":conversation_context.summary} if conversation_context else None),
            language=language,
        )
        ai1_ms = int((time.perf_counter() - ai_started) * 1000)

        evaluation = evaluate_ai1(
            normalized,
            ai1.answer,
            list(ai1.source_records),
            provider_ok=ai1.provider_status == "ok" and not ai1.fallback_required,
            grounding_status=ai1.grounding_status,
        )
        authoritative_citations = tuple(ai1.citations) or tuple(build_citations(list(ai1.source_records)))
        grounding = validate_grounding(
            normalized, ai1.answer, list(ai1.source_records), list(authoritative_citations),
            provider_ok=ai1.provider_status == "ok" and not ai1.fallback_required,
        )
        grounding_status = grounding.state
        # A provider-success answer with evidence is allowed to continue when
        # the backend can only establish derived grounding. Unknown/invalid
        # citation references remain a fallback trigger.
        fallback_needed = self._fallback_needed(evaluation) or grounding.state in {PARTIAL_EVIDENCE, INSUFFICIENT_EVIDENCE, FALLBACK}

        logger.info(
            "phase7_ai1_result provider=%s confidence=%.2f grounded=%s "
            "complete=%s fallback=%s execution_ms=%d",
            ai1.provider_status,
            evaluation.confidence,
            evaluation.grounded,
            evaluation.complete_enough,
            fallback_needed,
            ai1_ms,
        )

        if not fallback_needed:
            self.cache.set(query_key, {
                "reply": ai1.answer,
                "confidence": evaluation.confidence,
                "grounding_status": grounding_status,
                "citations": [c.model_dump() for c in authoritative_citations],
            }, self.cache_ttl_seconds)
            return AI1PipelineResult(
                reply=ai1.answer,
                source="ai1",
                confidence=evaluation.confidence,
                grounding_status=grounding_status,
                source_records=ai1.source_records,
                fallback_required=False,
                provider_status=ai1.provider_status,
                ai1_evaluation=evaluation,
                ai2_used=False,
                execution_ms=int((time.perf_counter() - started) * 1000),
                citations=authoritative_citations,
                resolved_query=resolved_query,
                context_used=context_used,
            )

        metrics.increment("fallback_requests")
        logger.info(
            "phase7_fallback_triggered ai1_provider=%s ai1_confidence=%.2f",
            ai1.provider_status,
            evaluation.confidence,
        )
        if settings.MAX_AI2_CALLS_PER_REQUEST < 1:
            return AI1PipelineResult(
                reply=ai1.answer,
                source="ai1_fallback",
                confidence=evaluation.confidence,
                grounding_status=grounding_status,
                source_records=ai1.source_records,
                fallback_required=True,
                provider_status=ai1.provider_status,
                ai1_evaluation=evaluation,
                ai2_used=False,
                execution_ms=int((time.perf_counter() - started) * 1000),
                citations=authoritative_citations,
                resolved_query=resolved_query,
                context_used=context_used,
            )

        metrics.increment("ai2_calls")
        ai2_answer = self.ai2_fallback.answer
        if "language" in inspect.signature(ai2_answer).parameters:
            ai2: AI2Result = ai2_answer(normalized, records, language=language)
        else:
            # Compatibility with existing injected/test fallback implementations.
            ai2 = ai2_answer(normalized, records)
        logger.info(
            "phase7_ai2_result provider=%s execution_ms=%d error=%s",
            ai2.provider_status,
            ai2.execution_ms,
            bool(ai2.error),
        )

        # Only attach source citations when AI #2 actually produced a grounded
        # answer. On provider failure ai2.answer is the generic safe-fallback
        # message ("I couldn't generate a confident answer..."), and appending
        # a "Sources:" footer to it would misleadingly imply that answer is
        # evidence-backed when it is not.
        ai2_succeeded = ai2.provider_status == "ok"
        final_citations = tuple(build_citations(list(records))) if ai2_succeeded else ()
        ai2_grounding = validate_grounding(
            normalized, ai2.answer, list(records), list(final_citations), provider_ok=ai2_succeeded
        )
        final_status = ai2_grounding.state if ai2_succeeded else FALLBACK
        final_answer = ai2.answer + format_citation_footer(list(final_citations)) if final_citations else ai2.answer
        self.cache.set(query_key, {
            "reply": final_answer,
            "confidence": ai2_grounding.confidence if ai2_succeeded else 0.0,
            "grounding_status": final_status,
            "citations": [c.model_dump() for c in final_citations],
        }, self.cache_ttl_seconds)
        return AI1PipelineResult(
            reply=final_answer,
            source="ai2" if ai2_succeeded else "safe_fallback",
            confidence=ai2_grounding.confidence if ai2_succeeded else 0.0,
            grounding_status=final_status,
            source_records=tuple(records),
            fallback_required=True,
            provider_status=ai2.provider_status,
            ai1_evaluation=evaluation,
            ai2_used=True,
            execution_ms=int((time.perf_counter() - started) * 1000),
            citations=final_citations,
            resolved_query=resolved_query,
            context_used=context_used,
        )
