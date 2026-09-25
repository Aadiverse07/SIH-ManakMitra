import sys
import types
from dataclasses import dataclass

import pytest


def test_prompt_contains_only_selected_records():
    from backend.app.services.ai.prompts import build_grounded_prompt

    prompt = build_grounded_prompt("What is IS 456?", [{
        "number": "IS 456:2000",
        "title": "Plain and Reinforced Concrete",
        "desc": "Concrete design code",
        "category": "civil",
        "dept": "CED 2",
        "status": "Active",
        "knowledge_status": "official_verified",
        "source": "BIS",
        "source_url": "https://www.services.bis.gov.in/",
    }])
    assert "IS 456:2000" in prompt
    assert "Plain and Reinforced Concrete" in prompt
    assert "entire database" not in prompt.lower()


def test_insufficient_context_does_not_call_llm():
    from backend.app.services.ai.answer_generator import generate_grounded_answer, FALLBACK

    called = []

    class FakeLLM:
        def generate(self, _): called.append(True)

    result = generate_grounded_answer("unknown", [], llm_service=FakeLLM())
    assert result.answer == FALLBACK
    assert result.fallback_required is True
    assert result.provider_status == "not_called"
    assert not called


def test_llm_failure_is_safe():
    from backend.app.services.ai.answer_generator import generate_grounded_answer

    class FakeLLM:
        def generate(self, _):
            raise RuntimeError("secret provider detail")

    # RuntimeError is intentionally not a provider LLMError; this verifies that
    # answer generation does not leak the exception through the public result.
    result = generate_grounded_answer("IS 456", [{"number": "IS 456:2000"}], llm_service=FakeLLM())
    assert result.fallback_required is True
    assert "secret provider detail" not in result.answer


def test_llm_success_returns_grounded_answer():
    from backend.app.services.ai.answer_generator import generate_grounded_answer

    class FakeLLM:
        def __init__(self):
            self.prompt = None
        def generate(self, prompt):
            self.prompt = prompt
            return "IS 456:2000 covers plain and reinforced concrete."

    record = {"number": "IS 456:2000", "title": "Plain and Reinforced Concrete"}
    service = FakeLLM()
    result = generate_grounded_answer("What is IS 456?", [record], llm_service=service)
    assert result.answer.startswith("IS 456:2000")
    # Phase 12 attaches backend-owned citation provenance to the grounding status.
    assert result.grounding_status == "retrieved_context_citations_backend_attached"
    assert not result.fallback_required
    assert "IS 456:2000" in service.prompt


def test_quota_failure_uses_safe_fallback():
    from backend.app.services.ai.answer_generator import generate_grounded_answer
    from backend.app.services.ai.llm_service import LLMQuotaError

    class FakeLLM:
        def generate(self, _):
            raise LLMQuotaError("do not expose this")

    result = generate_grounded_answer("IS 456", [{"number": "IS 456:2000"}], llm_service=FakeLLM())
    assert result.provider_status == "quota_exhausted"
    assert result.fallback_required is True
    assert "do not expose" not in result.answer


def test_pipeline_faq_short_circuits_retrieval():
    from backend.app.services.ai.pipeline import AI1Pipeline
    from backend.app.services.cache.service import InMemoryCacheService
    from backend.app.services.faq.service import FAQMatcher

    called = []

    def retrieval(*args, **kwargs):
        called.append(True)
        return []

    def generator(*args, **kwargs):
        raise AssertionError("AI must not run for a trusted FAQ hit")

    pipeline = AI1Pipeline(
        FAQMatcher([{"q": "What is BIS?", "a": "BIS is India's national standards body.", "category": "general"}]),
        InMemoryCacheService(),
        retrieval=retrieval,
        answer_generator=generator,
    )
    result = pipeline.answer("What is BIS?")
    assert result.source == "faq"
    assert result.reply.startswith("BIS is")
    assert not called


def test_pipeline_runs_retrieval_then_ai_and_caches():
    from backend.app.services.ai.pipeline import AI1Pipeline
    from backend.app.services.cache.service import InMemoryCacheService
    from backend.app.services.faq.service import FAQMatcher

    calls = []

    def retrieval(query, **kwargs):
        calls.append(("retrieval", query))
        return [{"number": "IS 800:2007", "title": "General Construction in Steel"}]

    def generator(question, records, **kwargs):
        calls.append(("ai", question, records))
        return types.SimpleNamespace(
            answer="IS 800:2007 covers general construction in steel.",
            grounding_status="retrieved_context_citations_backend_attached",
            source_records=tuple(records),
            fallback_required=False,
            provider_status="ok",
            citations=(),
        )

    pipeline = AI1Pipeline(FAQMatcher([]), InMemoryCacheService(),
                           retrieval=retrieval, answer_generator=generator)
    first = pipeline.answer("structural steel")
    second = pipeline.answer("structural steel")
    assert first.source == "ai1"
    assert second.source == "cache"
    assert [c[0] for c in calls] == ["retrieval", "ai"]


def test_malformed_request_is_rejected():
    from pydantic import ValidationError
    from backend.app.schemas.api import ChatRequest
    with pytest.raises(ValidationError):
        ChatRequest(message="")
    with pytest.raises(ValidationError):
        ChatRequest(message="x" * 10001)
