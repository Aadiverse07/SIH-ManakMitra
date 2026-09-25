"""Deterministic normalization for standards records."""
import re
from .base import IngestionRecord


def normalize_standard_number(value: str) -> str:
    value = re.sub(r"\s+", " ", str(value).strip().upper())
    value = re.sub(r"^IS\s*", "IS ", value)
    value = re.sub(r"\s*:\s*", ":", value)
    return value


def normalize_record(record: IngestionRecord) -> IngestionRecord:
    record.number = normalize_standard_number(record.number)
    record.title = re.sub(r"\s+", " ", record.title).strip()
    if record.description is not None:
        record.description = re.sub(r"\s+", " ", str(record.description)).strip()
    if record.category is not None:
        record.category = str(record.category).strip().lower()
    if record.dept is not None:
        record.dept = str(record.dept).strip()
    if record.status is not None:
        record.status = str(record.status).strip()
    if record.language is not None:
        record.language = str(record.language).strip()
    return record
