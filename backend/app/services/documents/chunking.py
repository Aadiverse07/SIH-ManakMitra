"""Traceable, page-aware document chunking."""
from __future__ import annotations
import hashlib
import re
from dataclasses import dataclass

@dataclass(frozen=True)
class DocumentChunk:
    chunk_index: int
    content: str
    page_number: int
    section: str | None
    clause: str | None
    content_hash: str

def normalize_text(text: str) -> str:
    text = text.replace("\x00", " ")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()

def chunk_pages(pages, max_chars: int = 1800, overlap: int = 250) -> list[DocumentChunk]:
    if max_chars < 300 or overlap >= max_chars:
        raise ValueError("Invalid chunking configuration.")
    out, index = [], 0
    for page in pages:
        text = normalize_text(page.text)
        if not text:
            continue
        start = 0
        while start < len(text):
            end = min(len(text), start + max_chars)
            if end < len(text):
                boundary = text.rfind("\n", start + max_chars // 2, end)
                if boundary > start:
                    end = boundary
            piece = text[start:end].strip()
            if piece:
                digest = hashlib.sha256(piece.encode("utf-8")).hexdigest()
                out.append(DocumentChunk(index, piece, page.page_number, page.section, page.clause, digest))
                index += 1
            if end >= len(text): break
            start = max(end - overlap, start + 1)
    return out
