"""Database-backed document processing."""
from backend.app.services.documents.repository import DocumentRepository
from backend.app.services.documents.storage import DocumentStorage
from backend.app.services.documents.parser import parse_document
from backend.app.services.documents.metadata import extract_metadata
from backend.app.services.documents.chunking import chunk_pages
from backend.app.services.documents.structured_extraction import extract_structures
from backend.app.services.documents.structured_repository import StructuredDocumentRepository

class DocumentProcessor:
    def __init__(self, repository=None, storage=None):
        self.repository = repository or DocumentRepository()
        self.structured_repository = StructuredDocumentRepository()
        self.storage = storage or DocumentStorage()

    def process(self, user_id: str, document_id: str, *, ocr_enabled=True):
        doc = self.repository.get(user_id, document_id)
        if not doc:
            raise LookupError("Document not found.")
        self.repository.update(user_id, document_id, {"processing_status": "processing", "processing_error": None})
        try:
            content = self.storage.read(doc["storage_path"])
            extension = "." + doc["original_filename"].rsplit(".", 1)[-1].lower()
            parsed = parse_document(content, extension, ocr_enabled=ocr_enabled)
            metadata = extract_metadata(doc["original_filename"], parsed, parsed.pdf_metadata)
            version = self.repository.get_version(document_id, doc["checksum"])
            if not version:
                version = self.repository.create_version({
                    "document_id": document_id,
                    "version_label": metadata.get("document_version"),
                    "revision": metadata.get("revision"),
                    "publication_date": metadata.get("publication_date"),
                    "effective_date": metadata.get("effective_date"),
                    "checksum": doc["checksum"],
                    "is_current": True,
                })
            chunks = chunk_pages(parsed.pages)
            structures = extract_structures(parsed.pages)
            page_rows = [{
                "document_id": document_id,
                "version_id": version["id"],
                "page_number": p.page_number,
                "text_content": p.text,
                "extraction_method": p.extraction_method,
                "section": p.section,
                "clause": p.clause,
            } for p in parsed.pages]
            self.repository.clear_children(document_id)
            self.structured_repository.clear(document_id)
            inserted_pages = self.repository.insert_pages(page_rows)
            page_ids = {p["page_number"]: p["id"] for p in inserted_pages}
            chunk_rows = [{
                "document_id": document_id,
                "version_id": version["id"],
                "page_id": page_ids.get(c.page_number),
                "chunk_index": c.chunk_index,
                "content": c.content,
                "section": c.section,
                "clause": c.clause,
                "page_number": c.page_number,
                "content_hash": c.content_hash,
                "metadata": {"extraction_method": next(
                    (p.extraction_method for p in parsed.pages if p.page_number == c.page_number), "text"
                )},
            } for c in chunks]
            metadata_rows = [{
                "document_id": document_id,
                "metadata_key": key,
                "metadata_value": str(value) if value is not None else None,
            } for key, value in metadata.items() if value is not None]
            self.repository.insert_chunks(chunk_rows)
            self.repository.insert_metadata(metadata_rows)

            clause_rows = []
            clause_ids = {}
            for item in structures["clauses"]:
                row = {
                    "document_id": document_id, "version_id": version["id"],
                    "page_id": page_ids.get(item["page_number"]),
                    "clause_number": item["clause_number"], "parent_clause": item["parent_clause"],
                    "title": item["title"], "text_content": item["text_content"],
                    "page_number": item["page_number"],
                }
                clause_rows.append(row)
            inserted_clauses = self.structured_repository.insert("document_clauses", clause_rows)
            for row in inserted_clauses:
                clause_ids[(row.get("clause_number"), row.get("page_number"))] = row.get("id")

            def with_clause(item):
                return clause_ids.get((item.get("clause_number"), item.get("page_number")))

            section_rows = [{"document_id": document_id, "version_id": version["id"], "page_id": page_ids.get(p.page_number),
                 "section_number": p.clause, "title": p.section, "section_type": "SECTION", "text_content": p.text[:4000], "page_number": p.page_number}
                for p in parsed.pages if p.section or p.clause]
            section_rows += [{"document_id": document_id, "version_id": version["id"], "page_id": page_ids.get(x["page_number"]),
                 "section_number": x["section_number"], "title": x["title"], "section_type": x["section_type"], "text_content": x["text_content"], "page_number": x["page_number"]}
                for x in structures["context_items"]]
            self.structured_repository.insert("document_sections", section_rows)
            self.structured_repository.insert("document_definitions", [
                {"document_id": document_id, "version_id": version["id"], "page_id": page_ids.get(x["page_number"]),
                 "clause_id": with_clause(x), "term": x["term"], "definition": x["definition"],
                 "clause_number": x["clause_number"], "page_number": x["page_number"]}
                for x in structures["definitions"]
            ])
            self.structured_repository.insert("document_tables", [
                {"document_id": document_id, "version_id": version["id"], "page_id": page_ids.get(x["page_number"]),
                 "clause_id": with_clause(x), "table_number": x["table_number"], "title": x["title"],
                 "headers": x["headers"], "rows": x["rows"], "units": x["units"], "footnotes": x["footnotes"],
                 "raw_text": x["raw_text"], "clause_number": x["clause_number"], "page_number": x["page_number"]}
                for x in structures["tables"]
            ])
            self.structured_repository.insert("document_formulas", [
                {"document_id": document_id, "version_id": version["id"], "page_id": page_ids.get(x["page_number"]),
                 "clause_id": with_clause(x), "expression_plain": x["expression_plain"], "expression_latex": x["expression_latex"],
                 "variables": x["variables"], "units": x["units"], "clause_number": x["clause_number"],
                 "page_number": x["page_number"], "source_text": x["source_text"]}
                for x in structures["formulas"]
            ])
            self.structured_repository.insert("document_requirements", [
                {"document_id": document_id, "version_id": version["id"], "page_id": page_ids.get(x["page_number"]),
                 "clause_id": with_clause(x), "statement": x["statement"], "classification": x["classification"],
                 "requirement_kind": x["requirement_kind"], "evidence": x["evidence"], "clause_number": x["clause_number"],
                 "page_number": x["page_number"]}
                for x in structures["requirements"]
            ])
            self.repository.update(user_id, document_id, {
                **metadata,
                "page_count": len(parsed.pages),
                "version_id": version["id"],
                "processing_status": "processed",
                "processing_error": None,
            })
            return self.repository.get(user_id, document_id)
        except Exception as exc:
            self.repository.update(user_id, document_id, {
                "processing_status": "failed",
                "processing_error": str(exc)[:2000],
            })
            raise
