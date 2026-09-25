"""Validation for uploaded BIS-related documents."""
from dataclasses import dataclass
from pathlib import Path
import hashlib
from backend.app.core.config import settings

ALLOWED_EXTENSIONS = {".pdf", ".txt", ".md"}
ALLOWED_MIME_TYPES = {
    "application/pdf",
    "text/plain",
    "text/markdown",
    "application/octet-stream",
}
MAX_DOCUMENT_BYTES = settings.DOCUMENT_MAX_SIZE_BYTES


@dataclass(frozen=True)
class ValidatedFile:
    filename: str
    extension: str
    mime_type: str
    size: int
    checksum: str
    content: bytes


def validate_document(filename: str, content: bytes, mime_type: str | None = None) -> ValidatedFile:
    safe_name = Path(filename or "").name
    if not safe_name or safe_name in {".", ".."}:
        raise ValueError("A document filename is required.")
    ext = Path(safe_name).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise ValueError("Unsupported document type. Supported formats: PDF, TXT and Markdown.")
    size = len(content)
    if size <= 0:
        raise ValueError("The uploaded document is empty.")
    if size > MAX_DOCUMENT_BYTES:
        raise ValueError("Document exceeds the 25 MB upload limit.")
    normalized_mime = (mime_type or "application/octet-stream").split(";")[0].strip().lower()
    if normalized_mime not in ALLOWED_MIME_TYPES:
        raise ValueError("Unsupported document MIME type.")
    if ext == ".pdf" and not content.startswith(b"%PDF"):
        raise ValueError("The uploaded file is not a valid PDF.")
    checksum = hashlib.sha256(content).hexdigest()
    return ValidatedFile(safe_name, ext, normalized_mime, size, checksum, content)
