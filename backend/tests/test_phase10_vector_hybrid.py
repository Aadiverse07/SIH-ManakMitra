import types


def test_embedding_service_batches_and_validates_dimension(monkeypatch):
    from backend.app.services.embedding_service import EmbeddingConfig, EmbeddingService

    class Provider:
        def __init__(self):
            self.calls = []

        def embed(self, texts):
            self.calls.append(list(texts))
            return [[0.1, 0.2, 0.3] for _ in texts]

    provider = Provider()
    service = EmbeddingService(provider)
    service.config = EmbeddingConfig(
        provider="test", model="test-model", dimensions=3,
        max_input_chars=20, batch_size=2, retries=0,
    )
    assert service.embed_batch([" one ", "two", "three"]) == [
        [0.1, 0.2, 0.3], [0.1, 0.2, 0.3], [0.1, 0.2, 0.3]
    ]
    assert len(provider.calls) == 2
    assert provider.calls[0] == ["one", "two"]


def test_hybrid_ranking_can_promote_semantic_match():
    from backend.app.services.hybrid_retriever import HybridRetriever
    from backend.app.services.retriever import RetrievalResult
    from backend.app.services.vector_retriever import VectorResult

    lexical_record = {
        "number": "IS 999:2000", "title": "Concrete testing methods",
        "category": "civil", "knowledge_status": "official_verified",
    }
    semantic_record = {
        "number": "IS 456:2000", "title": "Plain and Reinforced Concrete",
        "desc": "Code for structural concrete design", "category": "civil",
        "knowledge_status": "official_verified",
    }

    class Lexical:
        def search(self, *args, **kwargs):
            return [RetrievalResult(lexical_record, 10.0)]

    class Vector:
        def search(self, *args, **kwargs):
            return [VectorResult(
                semantic_record, 0.96, "kid", "standard", "IS456", "content", {}
            )]

    result = HybridRetriever(
        lexical=Lexical(), vector=Vector(),
        lexical_weight=0.35, vector_weight=0.55, metadata_weight=0.10,
    ).search("reinforced concrete", top_k=2)

    assert result[0].record["number"] == "IS 456:2000"
    assert result[0].vector_score == 0.96


def test_hybrid_deduplicates_same_source():
    from backend.app.services.hybrid_retriever import HybridRetriever
    from backend.app.services.retriever import RetrievalResult
    from backend.app.services.vector_retriever import VectorResult

    record = {
        "number": "IS 456:2000", "title": "Plain and Reinforced Concrete",
        "category": "civil", "knowledge_status": "official_verified",
    }

    class Lexical:
        def search(self, *args, **kwargs):
            return [RetrievalResult(record, 1000)]

    class Vector:
        def search(self, *args, **kwargs):
            return [VectorResult(record, 0.9, "id", "standard", "IS 456:2000", "x", {})]

    results = HybridRetriever(lexical=Lexical(), vector=Vector()).search("IS 456")
    assert len(results) == 1
    assert results[0].lexical_score > 0
    assert results[0].vector_score == 0.9


def test_vector_retriever_returns_empty_without_provider():
    from backend.app.services.vector_retriever import VectorRetriever

    class EmbeddingsUnavailable:
        available = False

    class DB:
        def rpc(self, *args, **kwargs):
            raise AssertionError("DB must not be called when embeddings are unavailable")

    assert VectorRetriever(EmbeddingsUnavailable(), DB()).search("IS 456") == []


def test_search_route_uses_hybrid(monkeypatch):
    import backend.app.api.routes.search as route

    monkeypatch.setattr(
        route, "search_hybrid",
        lambda *args, **kwargs: [{
            "number": "IS 456:2000",
            "title": "Plain and Reinforced Concrete",
            "knowledge_status": "official_verified",
            "status": "Active",
            "relevance_score": 0.92,
        }],
    )
    result = route.search("reinforced concrete", top_k=1)
    assert result["results"][0]["number"] == "IS 456:2000"


def test_pipeline_default_retriever_is_hybrid():
    from backend.app.services.ai.pipeline import AI1Pipeline
    from backend.app.services.hybrid_retriever import search_hybrid
    import inspect

    signature = inspect.signature(AI1Pipeline.__init__)
    default = signature.parameters["retrieval"].default
    assert default is search_hybrid
