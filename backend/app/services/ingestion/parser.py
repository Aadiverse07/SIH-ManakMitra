"""Parse raw BIS-shaped records into the ingestion model."""
from typing import Any
from .base import IngestionRecord


def parse_record(raw: dict[str, Any]) -> IngestionRecord:
    if not isinstance(raw, dict):
        raise ValueError("record must be an object")
    number = raw.get("is_number", raw.get("number"))
    title = raw.get("title")
    if number is None or title is None:
        raise ValueError("missing required standard number or title")
    return IngestionRecord(
        number=str(number),
        title=str(title),
        description=raw.get("description", raw.get("desc")),
        category=raw.get("category"),
        dept=raw.get("dept"),
        status=raw.get("status", "Active"),
        reaffirmed=raw.get("reaffirmed"),
        language=raw.get("language"),
        latest_revision_year=raw.get("latest_revision_year"),
        superseded_by=raw.get("superseded_by"),
        source=raw.get("source"),
        source_url=raw.get("source_url"),
        source_updated_at=raw.get("source_updated_at"),
        version_kind=raw.get("version_kind", "publication"),
        amendment_label=raw.get("amendment_label"),
        related_standard=raw.get("related_standard"),
        relationship_type=raw.get("relationship_type"),
        status_event_type=raw.get("status_event_type"),
        status_event_date=raw.get("status_event_date"),
        content_hash=raw.get("content_hash"),
        current_verified=bool(raw.get("current_verified", False)),
        raw=raw,
    )
