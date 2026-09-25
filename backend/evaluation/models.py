from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any

@dataclass(frozen=True)
class EvaluationCase:
    id: str
    question: str
    expected_topic: str | None = None
    expected_standard: str | None = None
    expected_version: str | None = None
    expected_clause: str | None = None
    expected_source: str | None = None
    expected_answer_characteristics: tuple[str, ...] = ()
    acceptable_evidence: tuple[str, ...] = ()
    expected_behavior_if_insufficient: str | None = None
    tags: tuple[str, ...] = ()

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "EvaluationCase":
        return cls(
            id=str(value["id"]), question=str(value["question"]),
            expected_topic=value.get("expected_topic"),
            expected_standard=value.get("expected_standard"),
            expected_version=value.get("expected_version"),
            expected_clause=value.get("expected_clause"),
            expected_source=value.get("expected_source"),
            expected_answer_characteristics=tuple(value.get("expected_answer_characteristics") or ()),
            acceptable_evidence=tuple(value.get("acceptable_evidence") or ()),
            expected_behavior_if_insufficient=value.get("expected_behavior_if_insufficient"),
            tags=tuple(value.get("tags") or ()),
        )

@dataclass
class CaseResult:
    case_id: str
    passed: bool
    retrieval: dict[str, Any] = field(default_factory=dict)
    grounding: dict[str, Any] = field(default_factory=dict)
    citation: dict[str, Any] = field(default_factory=dict)
    version: dict[str, Any] = field(default_factory=dict)
    context: dict[str, Any] = field(default_factory=dict)
    answer_quality: dict[str, Any] = field(default_factory=dict)
    hallucination: dict[str, Any] = field(default_factory=dict)
    latency_ms: dict[str, float] = field(default_factory=dict)
    error: str | None = None

@dataclass
class EvaluationReport:
    run_id: str
    started_at: str
    finished_at: str
    dataset_size: int
    passed: int
    failed: int
    metrics: dict[str, Any]
    cases: list[CaseResult]
    regression: dict[str, Any] = field(default_factory=dict)
    environment: str = "development"

    @property
    def overall_pass_rate(self) -> float:
        return self.passed / self.dataset_size if self.dataset_size else 0.0
