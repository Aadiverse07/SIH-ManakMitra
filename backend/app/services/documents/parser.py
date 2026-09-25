"""Document parsing with optional OCR fallback."""
from __future__ import annotations
from dataclasses import dataclass
from io import BytesIO
import re
from typing import Optional

@dataclass(frozen=True)
class ParsedPage:
    page_number: int
    text: str
    extraction_method: str = "text"
    section: Optional[str] = None
    clause: Optional[str] = None

@dataclass(frozen=True)
class ParsedDocument:
    pages: list[ParsedPage]
    pdf_metadata: dict

def _structure(text: str):
    section = None
    clause = None
    for line in text.splitlines():
        s = line.strip()
        if not s:
            continue
        clause_match = re.match(r"^((?:\d+\.)+\d*|\d+(?:\.\d+)+)\s+(.+)$", s)
        section_match = re.match(r"^(?:SECTION|Section)\s+([A-Z0-9 ._-]+)", s)
        if clause_match:
            clause = clause_match.group(1).rstrip(".")
            section = clause_match.group(2).strip()
        elif section_match:
            section = s
    return section, clause

def parse_pdf(content: bytes, ocr_enabled: bool = True) -> ParsedDocument:
    from pypdf import PdfReader
    reader = PdfReader(BytesIO(content))
    metadata = {}
    if reader.metadata:
        for key, value in reader.metadata.items():
            metadata[str(key).lstrip("/")] = str(value) if value is not None else ""
    pages = []
    for index, page in enumerate(reader.pages, start=1):
        text = (page.extract_text() or "").strip()
        method = "text"
        if not text and ocr_enabled:
            text = _ocr_pdf_page(content, index) or ""
            method = "ocr" if text else "text"
        section, clause = _structure(text)
        pages.append(ParsedPage(index, text, method, section, clause))
    return ParsedDocument(pages, metadata)

def _ocr_pdf_page(content: bytes, page_number: int) -> str:
    """Best-effort OCR; absence of OCR runtime never fails ingestion."""
    try:
        import fitz
        import pytesseract
        doc = fitz.open(stream=content, filetype="pdf")
        page = doc.load_page(page_number - 1)
        pix = page.get_pixmap(matrix=fitz.Matrix(1.8, 1.8), alpha=False)
        from PIL import Image
        image = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        return (pytesseract.image_to_string(image) or "").strip()
    except Exception:
        return ""

def parse_text(content: bytes) -> ParsedDocument:
    text = content.decode("utf-8-sig", errors="replace")
    pages = []
    # Form-feed is a conventional page separator in text exports.
    raw_pages = text.split("\f") or [text]
    for index, page_text in enumerate(raw_pages, start=1):
        page_text = page_text.strip()
        section, clause = _structure(page_text)
        pages.append(ParsedPage(index, page_text, "text", section, clause))
    return ParsedDocument(pages, {})

def parse_document(content: bytes, extension: str, ocr_enabled: bool = True) -> ParsedDocument:
    if extension == ".pdf":
        return parse_pdf(content, ocr_enabled=ocr_enabled)
    return parse_text(content)
