from backend.app.services.documents.validator import validate_document
from backend.app.services.documents.chunking import chunk_pages, normalize_text
from backend.app.services.documents.metadata import extract_metadata
from backend.app.services.documents.parser import ParsedDocument, ParsedPage, parse_text
import pytest

def test_pdf_validation_and_checksum():
    f = validate_document("x.pdf", b"%PDF-1.7 fake bytes", "application/pdf")
    assert f.extension == ".pdf"
    assert len(f.checksum) == 64

def test_invalid_file_rejected():
    with pytest.raises(ValueError):
        validate_document("x.exe", b"abc", "application/octet-stream")

def test_text_document_page_detection():
    parsed = parse_text("IS 456:2000\n1 Scope\n\f2 Terms\n2.1 Test method".encode())
    assert len(parsed.pages) == 2
    assert parsed.pages[1].page_number == 2

def test_chunk_traceability_and_normalization():
    pages = [ParsedPage(3, "1 Scope\n\n\nThis   is a document.", "text", "Scope", "1")]
    chunks = chunk_pages(pages, max_chars=300, overlap=20)
    assert chunks
    assert chunks[0].page_number == 3
    assert chunks[0].clause == "1"
    assert "This is a document." in chunks[0].content

def test_metadata_does_not_invent_revision():
    parsed = ParsedDocument([ParsedPage(1, "IS 1234:2026\nBIS STANDARD\nPublication date 2026-05-12")], {})
    meta = extract_metadata("IS_1234_2026.pdf", parsed, {})
    assert meta["standard_number"]
    assert meta["publication_date"] == "2026-05-12"
    assert meta["revision"] is None
