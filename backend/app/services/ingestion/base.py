"""Interfaces and result types for controlled BIS ingestion.

No network behavior is defined here. Production connectors must implement
BISSource and are expected to enforce their own authorization/robots/terms
checks before returning data.
"""
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Protocol


class ProcessingStatus(str, Enum):
    NEW = "NEW"
    UPDATED = "UPDATED"
    UNCHANGED = "UNCHANGED"
    FAILED = "FAILED"


@dataclass
class IngestionRecord:
    number: str
    title: str
    description: str | None = None
    category: str | None = None
    dept: str | None = None
    status: str = "Active"
    reaffirmed: int | None = None
    language: str | None = None
    latest_revision_year: int | None = None
    superseded_by: str | None = None
    source: str | None = None
    source_url: str | None = None
    source_updated_at: str | None = None
    collected_at: str | None = None
    validated_at: str | None = None
    validation_status: str | None = None
    version_kind: str = "publication"
    amendment_label: str | None = None
    related_standard: str | None = None
    relationship_type: str | None = None
    status_event_type: str | None = None
    status_event_date: str | None = None
    content_hash: str | None = None
    current_verified: bool = False
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass
class RecordResult:
    number: str
    status: ProcessingStatus
    reason: str | None = None


@dataclass
class IngestionRunResult:
    run_id: str
    status: str
    started_at: str
    completed_at: str | None
    records_seen: int = 0
    results: list[RecordResult] = field(default_factory=list)
    error: str | None = None

    @property
    def counts(self):
        return {s.value: sum(r.status == s for r in self.results) for s in ProcessingStatus}


class BISSource(Protocol):
    name: str

    def collect(self) -> list[dict[str, Any]]:
        """Return raw source records.

        A connector must only access an officially authorized source.
        """

def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()
