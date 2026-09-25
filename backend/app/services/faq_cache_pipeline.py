"""Phase 4 FAQ -> cache pipeline. AI/retrieval is intentionally not invoked."""
from dataclasses import dataclass
from backend.app.services.faq.service import FAQMatcher, normalize_question
from backend.app.services.cache.service import CacheService

@dataclass(frozen=True)
class PipelineResult:
    reply: str
    source: str
    confidence: float | None = None

class FAQCachePipeline:
    def __init__(self, faq_matcher: FAQMatcher, cache: CacheService, retrieval=None):
        self.faq_matcher = faq_matcher
        self.cache = cache
        self.retrieval = retrieval  # future seam; never called in Phase 4

    def answer(self, question: str, category: str | None = None) -> PipelineResult:
        normalized = normalize_question(question)
        match = self.faq_matcher.match(normalized, category=category)
        if match:
            key = CacheService.make_key("faq", normalized)
            cached = self.cache.get(key)
            if cached is not None:
                return PipelineResult(cached, "cache", match.confidence)
            self.cache.set(key, match.answer, ttl_seconds=3600)
            return PipelineResult(match.answer, "faq", match.confidence)

        key = CacheService.make_key("query", normalized)
        cached = self.cache.get(key)
        if cached is not None:
            return PipelineResult(cached, "cache", None)
        return PipelineResult(
            "I could not match that question to a trusted FAQ yet. Please try a specific BIS standard, certification scheme, or service question.",
            "miss",
            None,
        )
