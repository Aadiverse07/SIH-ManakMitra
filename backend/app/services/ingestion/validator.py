"""Validation rules for normalized BIS standard records."""
from dataclasses import dataclass
from .base import IngestionRecord


@dataclass
class ValidationResult:
    valid: bool
    errors: list[str]


ALLOWED_STATUS = {"Active", "Superseded", "Withdrawn"}
ALLOWED_VERSION_KINDS = {"publication", "revision", "reaffirmation", "amendment", "unknown"}
ALLOWED_RELATIONSHIPS = {"supersedes", "superseded_by", "amends", "amended_by", "reaffirms", "withdrawn", "replaced_by"}
ALLOWED_EVENTS = {"active", "reaffirmed", "amended", "withdrawn", "superseded", "replaced", "published", "revised", "unknown"}


def validate_record(record: IngestionRecord) -> ValidationResult:
    errors = []
    if not record.number.startswith("IS "):
        errors.append("standard number must start with 'IS '")
    if not record.title.strip():
        errors.append("title is required")
    if record.status not in ALLOWED_STATUS:
        errors.append(f"status must be one of {sorted(ALLOWED_STATUS)}")
    if record.version_kind not in ALLOWED_VERSION_KINDS:
        errors.append(f"version_kind must be one of {sorted(ALLOWED_VERSION_KINDS)}")
    if record.relationship_type and record.relationship_type not in ALLOWED_RELATIONSHIPS:
        errors.append(f"relationship_type must be one of {sorted(ALLOWED_RELATIONSHIPS)}")
    if record.status_event_type and record.status_event_type not in ALLOWED_EVENTS:
        errors.append(f"status_event_type must be one of {sorted(ALLOWED_EVENTS)}")
    if record.superseded_by and record.superseded_by == record.number:
        errors.append("superseded_by cannot reference itself")
    return ValidationResult(not errors, errors)
