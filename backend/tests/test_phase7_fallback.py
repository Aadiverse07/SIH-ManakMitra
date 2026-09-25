import types

from backend.app.services.ai.evaluation import AI1Evaluation
from backend.app.services.ai.fallback import AI2Result, AI2_SAFE_FALLBACK
from backend.app.services.ai.pipeline import AI1Pipeline
from backend.app.services.cache.service import InMemoryCacheService
from backend.app.services.faq.service import FAQMatcher


def make_pipeline(ai1_answer, *, provider_status="ok", ai1_fallback=False,
                   ai2_answer="AI #2 response", ai2_status="ok"):
    calls = []

    def retrieval(*args, **kwargs):
        calls.append("retrieval")
        return [{
            "number": "IS 800:2007",
            "title": "General Construction in Steel",
            "desc": "Steel construction standard",
            "knowledge_status": "official_verified",
            "source": "BIS",
            "status": "Active",
        }]

    def generator(question, records, **kwargs):
        calls.append("ai1")
        return types.SimpleNamespace(
            answer=ai1_answer,
            grounding_status="retrieved_context_citations_backend_attached",
            source_records=tuple(records),
            fallback_required=ai1_fallback,
            provider_status=provider_status,
            citations=(),
        )

    class FakeAI2:
        def answer(self, question, records):
            calls.append("ai2")
            return AI2Result(ai2_answer, ai2_status, 3, None if ai2_status == "ok" else "provider_error")

    return AI1Pipeline(
        FAQMatcher([]),
        InMemoryCacheService(),
        retrieval=retrieval,
        answer_generator=generator,
        ai2_fallback=FakeAI2(),
    ), calls


def test_ai1_solves_ai2_not_called():
    pipeline, calls = make_pipeline(
        "IS 800:2007 covers general construction in steel."
    )
    result = pipeline.answer("What is IS 800?")
    assert result.source == "ai1"
    assert result.ai2_used is False
    assert calls == ["retrieval", "ai1"]


def test_ai1_fails_ai2_called():
    pipeline, calls = make_pipeline(
        "I couldn't generate a grounded BIS answer right now. Please try again later.",
        ai1_fallback=True,
    )
    result = pipeline.answer("What is IS 800?")
    assert result.source == "ai2"
    assert result.ai2_used is True
    assert calls == ["retrieval", "ai1", "ai2"]


def test_low_confidence_triggers_ai2():
    # The answer has context but does not contain an identifying record term,
    # so the conservative local grounding evaluator lowers confidence.
    pipeline, calls = make_pipeline("This explanation is uncertain and does not establish the requested facts.")
    result = pipeline.answer("Explain structural steel")
    assert result.ai2_used is True
    assert calls == ["retrieval", "ai1", "ai2"]


def test_ai2_failure_is_graceful():
    pipeline, calls = make_pipeline(
        "short",
        ai2_answer=AI2_SAFE_FALLBACK,
        ai2_status="provider_error",
    )
    result = pipeline.answer("Explain structural steel")
    assert result.source == "safe_fallback"
    assert result.reply == AI2_SAFE_FALLBACK
    assert result.ai2_used is True


def test_both_fail_safe_without_provider_error_leak():
    pipeline, calls = make_pipeline(
        "",
        provider_status="provider_error",
        ai1_fallback=True,
        ai2_answer=AI2_SAFE_FALLBACK,
        ai2_status="provider_error",
    )
    result = pipeline.answer("Explain structural steel")
    assert result.reply == AI2_SAFE_FALLBACK
    assert result.source == "safe_fallback"
    assert result.ai2_used is True
    assert result.provider_status == "provider_error"


def test_ambiguous_versions_do_not_skip_ai1(monkeypatch):
    """Unresolved version ambiguity must preserve evidence for AI #1.

    Before this fix, constrain_records_to_version() returned [] for multiple
    versions without an authoritative current marker, which made
    generate_grounded_answer() return provider=not_called and forced every
    request into AI #2.
    """
    import backend.app.services.ai.pipeline as pipeline_module

    class FakeAI2:
        def answer(self, question, records):
            return AI2Result("AI2", "ok", 1, None)

    def retrieval(*args, **kwargs):
        return [
            {"number": "IS 456:2000", "title": "Concrete", "knowledge_status": "official_verified"},
            {"number": "IS 456:1978", "title": "Concrete", "knowledge_status": "official_verified"},
        ]

    calls = []
    def generator(question, records, **kwargs):
        calls.append(records)
        return types.SimpleNamespace(
            answer="The retrieved versions must be compared separately.",
            grounding_status="retrieved_context_citations_backend_attached",
            source_records=tuple(records), fallback_required=False,
            provider_status="ok", citations=(),
        )

    pipeline = AI1Pipeline(
        FAQMatcher([]), InMemoryCacheService(), retrieval=retrieval,
        answer_generator=generator, ai2_fallback=FakeAI2(),
    )
    result = pipeline.answer("Compare the old and latest versions of the concrete standard")
    assert calls and len(calls[0]) == 2
    assert result.provider_status == "ok"
    assert result.source == "ai1"
