"""Phase 13 standard lifecycle/version intelligence.

This module is deliberately source-grounded. It never infers that the newest
year is authoritative, and it never invents amendment/supersession facts.
Database relationships/events are authoritative only when explicitly present.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Iterable, Optional


_VERSION_RE = re.compile(r"\bIS\s+([0-9]{1,6}(?:\s*\([^)]*\))?)\s*:\s*(\d{4})\b", re.I)


@dataclass(frozen=True)
class VersionResolution:
    requested_version: str | None
    selected_version_id: str | None
    selected_label: str | None
    reason: str
    current_verified: bool = False
    relationship_types: tuple[str, ...] = ()


def parse_version_reference(text: str) -> tuple[str, int] | None:
    m = _VERSION_RE.search(text or "")
    if not m:
        return None
    label = "IS " + re.sub(r"\s+", " ", m.group(1)).strip() + ":" + m.group(2)
    return label, int(m.group(2))


def _number(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip().lower()


def _is_explicit_historical(query: str) -> bool:
    q = (query or "").lower()
    return bool(re.search(r"\b(?:in|from|version|edition|revision)\s+(?:the\s+)?(?:19|20)\d{2}\b", q))


class VersionResolver:
    """Resolve version context from already-retrieved/source-backed records.

    `relationships` may contain normalized relationship rows keyed by version
    ids. `current_version_id` should only be supplied when a trusted source has
    explicitly identified it as current/authoritative.
    """

    def __init__(
        self,
        versions: Iterable[dict[str, Any]] | None = None,
        relationships: Iterable[dict[str, Any]] | None = None,
        status_events: Iterable[dict[str, Any]] | None = None,
    ):
        self.versions = list(versions or [])
        self.relationships = list(relationships or [])
        self.status_events = list(status_events or [])

    def _requested_label(self, query: str) -> str | None:
        parsed = parse_version_reference(query)
        return parsed[0] if parsed else None

    def resolve(
        self,
        query: str,
        candidates: list[dict[str, Any]],
        *,
        current_version_id: str | None = None,
    ) -> VersionResolution:
        requested = self._requested_label(query)
        if not candidates:
            return VersionResolution(requested, None, None, "no_candidates")

        # Explicit version request wins over current preference.
        if requested:
            exact = [
                c for c in candidates
                if _number(c.get("is_number") or c.get("version_label")) == _number(requested)
            ]
            if exact:
                c = exact[0]
                return VersionResolution(
                    requested, str(c.get("version_id") or c.get("id") or "") or None,
                    c.get("is_number") or c.get("version_label"),
                    "explicit_version_match",
                    current_verified=bool(c.get("current_verified")),
                )

        if current_version_id:
            current = [c for c in candidates if str(c.get("version_id") or c.get("id")) == str(current_version_id)]
            if current:
                c = current[0]
                return VersionResolution(
                    requested,
                    str(c.get("version_id") or c.get("id")),
                    c.get("is_number") or c.get("version_label"),
                    "source_verified_current_version",
                    current_verified=True,
                )

        verified_current = [c for c in candidates if c.get("current_verified") is True]
        if len(verified_current) == 1:
            c = verified_current[0]
            return VersionResolution(
                requested,
                str(c.get("version_id") or c.get("id") or "") or None,
                c.get("is_number") or c.get("version_label"),
                "source_verified_current_version",
                current_verified=True,
            )

        if _is_explicit_historical(query):
            # Historical wording without an exact parsed version is not a reason
            # to pick a year. Preserve the ambiguity.
            return VersionResolution(requested, None, None, "historical_request_requires_verified_version")

        # A generic standard query may return a verified active revision plus an
        # explicitly superseded historical revision. Prefer the non-superseded
        # candidate only when it is unique; this does NOT label it current.
        non_superseded = [
            c for c in candidates
            if str(c.get("status") or c.get("lifecycle_status") or "").lower() not in {"superseded", "withdrawn", "replaced"}
        ]
        if len(non_superseded) == 1 and len(candidates) > 1:
            c = non_superseded[0]
            return VersionResolution(
                requested, str(c.get("version_id") or c.get("id") or "") or None,
                c.get("is_number") or c.get("version_label"),
                "unique_non_superseded_candidate",
                current_verified=bool(c.get("current_verified")),
            )

        # Do not select by newest year. If exactly one candidate remains, it is
        # safe to use that candidate without calling it "current".
        if len(candidates) == 1:
            c = candidates[0]
            return VersionResolution(
                requested,
                str(c.get("version_id") or c.get("id") or "") or None,
                c.get("is_number") or c.get("version_label"),
                "single_candidate",
                current_verified=bool(c.get("current_verified")),
            )

        return VersionResolution(requested, None, None, "multiple_versions_without_authoritative_resolution")

    @staticmethod
    def annotate_candidates(
        candidates: list[dict[str, Any]],
        *,
        current_version_id: str | None = None,
    ) -> list[dict[str, Any]]:
        out = []
        for c in candidates:
            item = dict(c)
            item["version_context"] = {
                "version_id": item.get("version_id"),
                "version_label": item.get("version_label") or item.get("is_number"),
                "publication_year": item.get("publication_year"),
                "version_kind": item.get("version_kind"),
                "current_verified": bool(
                    current_version_id and str(item.get("version_id")) == str(current_version_id)
                ),
            }
            out.append(item)
        return out


def relation_inverse(relationship_type: str) -> str | None:
    return {
        "supersedes": "superseded_by",
        "superseded_by": "supersedes",
        "amends": "amended_by",
        "amended_by": "amends",
        "reaffirms": "reaffirms",
        "withdrawn": "withdrawn",
        "replaced_by": "replaced_by",
    }.get(relationship_type)


def detect_source_change(previous: dict[str, Any] | None, current: dict[str, Any]) -> dict[str, Any]:
    """Compare source-backed records without interpreting the change."""
    if previous is None:
        return {"change_type": "new_version", "changed_fields": list(current.keys())}
    changed = sorted(
        k for k in set(previous) | set(current)
        if previous.get(k) != current.get(k)
    )
    if not changed:
        return {"change_type": "unchanged", "changed_fields": []}
    if "status" in changed:
        change_type = "status_change"
    elif "content_hash" in changed:
        change_type = "content_change"
    else:
        change_type = "metadata_change"
    return {"change_type": change_type, "changed_fields": changed}


def constrain_records_to_version(
    records: list[dict[str, Any]], query: str, *, current_version_id: str | None = None
) -> tuple[list[dict[str, Any]], VersionResolution]:
    """Prevent incompatible versions from reaching AI #1."""
    resolver = VersionResolver()
    resolution = resolver.resolve(query, records, current_version_id=current_version_id)
    if not records:
        return [], resolution
    if resolution.selected_version_id:
        selected = [
            r for r in records
            if str(r.get("version_id") or r.get("id") or "") == resolution.selected_version_id
            or _number(r.get("version_label") or r.get("is_number")) == _number(resolution.selected_label)
        ]
        return selected, resolution
    labels = {_number(r.get("version_label") or r.get("number") or r.get("is_number")) for r in records}
    labels.discard("")
    if len(labels) > 1:
        return [], resolution
    return records, resolution
