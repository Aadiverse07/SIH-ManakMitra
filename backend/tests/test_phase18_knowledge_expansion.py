from pathlib import Path
import inspect


def test_phase18_migration_exists_and_contains_official_sources():
    path = Path(__file__).resolve().parents[2] / "database" / "migrations" / "0011_phase18_knowledge_expansion.sql"
    text = path.read_text(encoding="utf-8")
    assert "knowledge_documents" in text
    assert "Bureau of Indian Standards" in text
    assert "official_verified" in text
    assert "IS 1417:2016" in text


def test_phase18_indexer_indexes_knowledge_documents():
    path = Path(__file__).resolve().parents[1] / "scripts" / "index_embeddings.py"
    text = path.read_text(encoding="utf-8")
    assert '("knowledge_documents", _document)' in text


def test_phase18_hybrid_search_supports_non_standard_knowledge():
    path = Path(__file__).resolve().parents[1] / "app" / "services" / "hybrid_retriever.py"
    text = path.read_text(encoding="utf-8")
    assert '"faq"' in text
    assert '"document"' in text
    assert '"certification_step"' in text


def test_phase18_search_route_stays_standards_only():
    path = Path(__file__).resolve().parents[1] / "app" / "api" / "routes" / "search.py"
    text = path.read_text(encoding="utf-8")
    assert 'knowledge_types=("standard",)' in text
