"""Application wiring for the Phase 4 FAQ/cache pipeline."""
from backend.app.services.data_service import list_faqs
from backend.app.services.faq.service import FAQMatcher
from backend.app.services.cache.service import InMemoryCacheService
from backend.app.services.faq_cache_pipeline import FAQCachePipeline

_cache = InMemoryCacheService()

def get_pipeline():
    return FAQCachePipeline(FAQMatcher(list_faqs()), _cache)
