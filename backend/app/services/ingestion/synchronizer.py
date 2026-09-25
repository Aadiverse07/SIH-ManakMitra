"""Controlled, idempotent synchronization into the existing standards table."""
from typing import Any
from uuid import uuid4
from .base import ProcessingStatus, IngestionRunResult, RecordResult, utc_now
from .parser import parse_record
from .normalizer import normalize_record
from .validator import validate_record

DATA_FIELDS = (
    "is_number", "title", "description", "category", "dept", "status",
    "reaffirmed", "language", "latest_revision_year", "superseded_by",
    "source", "source_url", "source_updated_at",
)


class StandardsRepository:
    """Small adapter around Supabase so synchronization is easy to test."""

    def __init__(self, client):
        self.client = client

    def get_by_number(self, number: str):
        data = (self.client.table("standards").select("*")
                .eq("is_number", number).limit(1).execute().data)
        return data[0] if data else None

    def insert(self, payload: dict[str, Any]):
        return self.client.table("standards").insert(payload).execute()

    def update(self, number: str, payload: dict[str, Any]):
        return self.client.table("standards").update(payload).eq("is_number", number).execute()

    def sync_lifecycle(self, standard_number: str, record):
        """Persist only lifecycle facts explicitly supplied by the source record."""
        standard_rows = (self.client.table("standards").select("id,is_number")
                         .eq("is_number", standard_number).limit(1).execute().data)
        if not standard_rows:
            return
        standard_id = standard_rows[0]["id"]
        version_payload = {
            "standard_id": standard_id,
            "version_label": standard_number,
            "publication_year": int(standard_number[-4:]) if standard_number[-4:].isdigit() else None,
            "version_kind": record.version_kind,
            "source": record.source,
            "source_url": record.source_url,
            "source_updated_at": record.source_updated_at,
            "content_hash": record.content_hash,
            "current_verified": record.current_verified,
        }
        version_response = (self.client.table("standard_versions")
                            .upsert(version_payload, on_conflict="standard_id,version_label")
                            .execute())
        version_rows = version_response.data or []
        if not version_rows:
            version_rows = (self.client.table("standard_versions").select("*")
                            .eq("standard_id", standard_id)
                            .eq("version_label", standard_number).limit(1).execute().data)
        if not version_rows:
            return
        version_id = version_rows[0]["id"]

        if record.amendment_label:
            self.client.table("standard_amendments").upsert({
                "standard_version_id": version_id,
                "amendment_label": record.amendment_label,
                "source": record.source, "source_url": record.source_url,
                "source_updated_at": record.source_updated_at,
                "content_hash": record.content_hash,
            }, on_conflict="standard_version_id,amendment_label").execute()

        if record.status_event_type:
            self.client.table("standard_status_events").upsert({
                "standard_version_id": version_id,
                "event_type": record.status_event_type,
                "event_date": record.status_event_date,
                "source": record.source, "source_url": record.source_url,
                "source_updated_at": record.source_updated_at,
                "content_hash": record.content_hash,
            }, on_conflict="standard_version_id,event_type,event_date,content_hash").execute()

        if record.related_standard and record.relationship_type:
            target = (self.client.table("standards").select("id,is_number")
                      .eq("is_number", record.related_standard).limit(1).execute().data)
            if target:
                target_version = (self.client.table("standard_versions").select("id")
                                  .eq("standard_id", target[0]["id"])
                                  .eq("version_label", record.related_standard).limit(1).execute().data)
                if target_version:
                    self.client.table("standard_relationships").upsert({
                        "from_version_id": version_id,
                        "to_version_id": target_version[0]["id"],
                        "relationship_type": record.relationship_type,
                        "source": record.source, "source_url": record.source_url,
                        "source_updated_at": record.source_updated_at,
                        "evidence_note": "Source-supplied relationship",
                        "content_hash": record.content_hash,
                    }, on_conflict="from_version_id,to_version_id,relationship_type").execute()

    def start_run(self, run_id, source_name, started_at):
        return (self.client.table("ingestion_runs").insert({
            "run_id": run_id, "source_name": source_name,
            "started_at": started_at, "status": "RUNNING",
        }).execute())

    def finish_run(self, run_id, result):
        counts = result.counts
        return (self.client.table("ingestion_runs").update({
            "completed_at": result.completed_at, "status": result.status,
            "records_seen": result.records_seen,
            "new_count": counts["NEW"], "updated_count": counts["UPDATED"],
            "unchanged_count": counts["UNCHANGED"], "failed_count": counts["FAILED"],
            "error": result.error,
        }).eq("run_id", run_id).execute())


def _same_data(existing: dict[str, Any] | None, payload: dict[str, Any]) -> bool:
    if existing is None:
        return False
    return all(existing.get(k) == payload.get(k) for k in DATA_FIELDS)


def synchronize(source, repository, run_id: str | None = None, retries: int = 0) -> IngestionRunResult:
    run_id = run_id or str(uuid4())
    started = utc_now()
    try:
        if hasattr(repository, "start_run"):
            repository.start_run(run_id, getattr(source, "name", source.__class__.__name__), started)

        raw_records = None
        last_error = None
        for attempt in range(retries + 1):
            try:
                raw_records = source.collect()
                break
            except Exception as exc:
                last_error = exc
                if attempt == retries:
                    result = IngestionRunResult(run_id, "FAILED", started, utc_now(), error=str(last_error))
                    if hasattr(repository, "finish_run"): repository.finish_run(run_id, result)
                    return result

        results: list[RecordResult] = []
        seen = set()
        for raw in raw_records:
            try:
                record = normalize_record(parse_record(raw))
                if record.number in seen:
                    results.append(RecordResult(record.number, ProcessingStatus.FAILED, "duplicate in source batch"))
                    continue
                seen.add(record.number)
                validation = validate_record(record)
                if not validation.valid:
                    results.append(RecordResult(record.number, ProcessingStatus.FAILED, "; ".join(validation.errors)))
                    continue

                existing = repository.get_by_number(record.number)
                payload = {
                    "is_number": record.number, "title": record.title,
                    "description": record.description, "category": record.category,
                    "dept": record.dept, "status": record.status,
                    "reaffirmed": record.reaffirmed, "language": record.language,
                    "latest_revision_year": record.latest_revision_year,
                    "superseded_by": record.superseded_by, "source": record.source,
                    "source_url": record.source_url, "source_updated_at": record.source_updated_at,
                }
                if existing is None:
                    now = utc_now()
                    payload.update({"collected_at": now, "validated_at": now, "validation_status": "validated"})
                    repository.insert(payload)
                    if hasattr(repository, "sync_lifecycle"):
                        repository.sync_lifecycle(record.number, record)
                    results.append(RecordResult(record.number, ProcessingStatus.NEW))
                elif _same_data(existing, payload):
                    if hasattr(repository, "sync_lifecycle"):
                        repository.sync_lifecycle(record.number, record)
                    results.append(RecordResult(record.number, ProcessingStatus.UNCHANGED))
                else:
                    now = utc_now()
                    payload.update({"collected_at": now, "validated_at": now, "validation_status": "validated"})
                    repository.update(record.number, payload)
                    if hasattr(repository, "sync_lifecycle"):
                        repository.sync_lifecycle(record.number, record)
                    results.append(RecordResult(record.number, ProcessingStatus.UPDATED))
            except Exception as exc:
                number = str(raw.get("is_number", raw.get("number", "<unknown>"))) if isinstance(raw, dict) else "<unknown>"
                results.append(RecordResult(number, ProcessingStatus.FAILED, str(exc)))

        failed = any(r.status == ProcessingStatus.FAILED for r in results)
        result = IngestionRunResult(run_id, "PARTIAL" if failed else "SUCCESS",
            started, utc_now(), records_seen=len(raw_records), results=results)
        if hasattr(repository, "finish_run"): repository.finish_run(run_id, result)
        return result
    except Exception as exc:
        result = IngestionRunResult(run_id, "FAILED", started, utc_now(), error=str(exc))
        if hasattr(repository, "finish_run"):
            try: repository.finish_run(run_id, result)
            except Exception: pass
        return result
