"""Production-oriented document ingestion orchestration."""
from __future__ import annotations
from backend.app.services.documents.parser import parse_document
from backend.app.services.documents.metadata import extract_metadata
from backend.app.services.documents.chunking import chunk_pages
from backend.app.services.documents.storage import DocumentStorage
from backend.app.services.documents.validator import validate_document

class DocumentIngestionService:
    def __init__(self, storage=None):
        self.storage = storage or DocumentStorage()

    def validate(self, filename, content, mime_type=None):
        return validate_document(filename, content, mime_type)

    def parse(self, validated, ocr_enabled=True):
        return parse_document(validated.content, validated.extension, ocr_enabled=ocr_enabled)

    def prepare(self, validated, ocr_enabled=True):
        parsed = self.parse(validated, ocr_enabled=ocr_enabled)
        metadata = extract_metadata(validated.filename, parsed, parsed.pdf_metadata)
        chunks = chunk_pages(parsed.pages)
        return parsed, metadata, chunks
