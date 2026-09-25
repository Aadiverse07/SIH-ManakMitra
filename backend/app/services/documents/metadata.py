"""Conservative metadata extraction. No values are invented."""
from __future__ import annotations
from datetime import date
import re
from pathlib import Path

def _date(value: str | None):
    if not value:
        return None
    m = re.search(r"\b(19|20)\d{2}[-/.](\d{1,2})[-/.](\d{1,2})\b", value)
    if not m:
        m = re.search(r"\b(\d{1,2})[-/.](\d{1,2})[-/.]((?:19|20)\d{2})\b", value)
        if m:
            try: return date(int(m.group(3)), int(m.group(2)), int(m.group(1))).isoformat()
            except ValueError: return None
        return None
    try: return date(int(m.group(0)[:4]), int(m.group(2)), int(m.group(3))).isoformat()
    except ValueError: return None

def extract_metadata(filename: str, parsed, pdf_metadata: dict | None = None) -> dict:
    first_text = "\n".join(p.text for p in parsed.pages[:2])
    meta = pdf_metadata or {}
    title = meta.get("Title") or None
    if not title:
        for line in first_text.splitlines():
            line = line.strip()
            if 5 <= len(line) <= 180 and not re.match(r"^(page|contents|index)\b", line, re.I):
                title = line
                break
    title = title or Path(filename).stem.replace("_", " ").replace("-", " ").strip()

    standard = None
    for source in [filename, first_text]:
        m = re.search(r"\b(?:IS|IS/ISO|IS\s*/\s*IEC|IS\s+ISO/IEC)\s*[-:]?\s*\d+(?:\s*:\s*\d{4})?\b", source, re.I)
        if m:
            standard = re.sub(r"\s+", " ", m.group(0)).strip()
            break

    revision = None
    m = re.search(r"\b(?:revision|rev\.?|edition)\s*[:.]?\s*([A-Za-z0-9 ._-]+)", first_text, re.I)
    if m:
        revision = m.group(1).strip()[:80]

    publication_date = _date(first_text)
    document_type = "standard" if standard else "other"
    lower = first_text.lower()
    if "certificate" in lower: document_type = "certification"
    elif "guideline" in lower or "guidelines" in lower: document_type = "guideline"
    elif "circular" in lower: document_type = "circular"
    elif "amendment" in lower: document_type = "amendment"
    elif "fee" in lower and "schedule" in lower: document_type = "fee_schedule"
    elif "form" in lower: document_type = "form"
    elif "testing" in lower: document_type = "testing"

    return {
        "title": title[:255],
        "document_type": document_type,
        "standard_number": standard,
        "revision": revision,
        "publication_date": publication_date,
        "effective_date": None,
        "language": None,
        "document_version": revision,
    }
