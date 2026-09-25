from backend.app.services.faq.service import FAQMatcher, normalize_question
from backend.app.services.cache.service import CacheService, InMemoryCacheService
from backend.app.services.faq_cache_pipeline import FAQCachePipeline

FAQS = [
    {"q": "What is the ISI mark?", "a": "The ISI mark indicates conformity to the relevant Indian Standard.", "category": "certification"},
    {"q": "How do I get BIS certification for my product?", "a": "Follow the BIS application, testing and evaluation process.", "category": "certification"},
]

def test_exact_and_normalized_match():
    matcher = FAQMatcher(FAQS)
    assert matcher.match("What is the ISI mark?").confidence == 1.0
    assert matcher.match("  WHAT IS THE ISI MARK?  ") is not None

def test_paraphrase_intent_match():
    assert FAQMatcher(FAQS).match("What does ISI mean?") is not None

def test_category_aware_matching():
    match = FAQMatcher(FAQS).match("What is ISI?", category="certification")
    assert match is not None and match.category == "certification"

def test_faq_miss_does_not_call_retrieval():
    called = []
    def retrieval(_): called.append(True)
    result = FAQCachePipeline(FAQMatcher(FAQS), InMemoryCacheService(), retrieval).answer("random unrelated question")
    assert result.source == "miss" and not called

def test_cache_hit_after_faq_resolution():
    cache = InMemoryCacheService()
    pipeline = FAQCachePipeline(FAQMatcher(FAQS), cache)
    assert pipeline.answer("What is the ISI mark?").source == "faq"
    assert pipeline.answer("What is the ISI mark?").source == "cache"

def test_cache_miss_and_key_consistency():
    cache = InMemoryCacheService()
    key1 = CacheService.make_key("faq", " What IS the ISI mark? ")
    key2 = CacheService.make_key("faq", "what is the isi mark?")
    assert key1 == key2
    assert cache.get(key1) is None

def test_cache_expiration_and_delete():
    import time
    cache = InMemoryCacheService()
    cache.set("k", "v", 0.01)
    assert cache.get("k") == "v"
    time.sleep(0.02)
    assert cache.get("k") is None
    cache.set("k", "v", 1)
    cache.delete("k")
    assert cache.get("k") is None

def test_normalize_question():
    assert normalize_question("  What is ISI? ") == "what is isi"
