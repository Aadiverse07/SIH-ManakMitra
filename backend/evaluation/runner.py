from __future__ import annotations
import json, logging, time, uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable
from .models import EvaluationCase, EvaluationReport, CaseResult
from .metrics import retrieval_metrics, regression_delta
from .evaluators import evaluate_case

logger=logging.getLogger(__name__)
DATASET_PATH=Path(__file__).with_name("dataset.json")

def load_dataset(path: str|Path|None=None)->list[EvaluationCase]:
    p=Path(path or DATASET_PATH)
    return [EvaluationCase.from_dict(x) for x in json.loads(p.read_text(encoding="utf-8"))]

def _ids(records:list[dict[str,Any]])->list[str]:
    out=[]
    for r in records:
        out.append(str(r.get("number") or r.get("is_number") or r.get("id") or r.get("source_id") or ""))
    return out

def run_evaluation(
    pipeline: Callable[..., Any],
    *,
    dataset: list[EvaluationCase]|None=None,
    retrieval_runner: Callable[[str],dict[str,list[dict[str,Any]]]]|None=None,
    baseline_metrics: dict[str,float]|None=None,
    environment: str="development",
)->EvaluationReport:
    cases=dataset or load_dataset()
    run_id=str(uuid.uuid4())
    started=datetime.now(timezone.utc)
    results=[]
    ranking_sets={"keyword":[],"vector":[],"hybrid":[]}
    relevant_sets=[]
    for case in cases:
        t0=time.perf_counter()
        try:
            if retrieval_runner:
                retrievals=retrieval_runner(case.question)
            else:
                retrievals={}
            for kind in ("keyword","vector","hybrid"):
                ranking_sets[kind].append(_ids(retrievals.get(kind,[])))
            relevant=set([case.expected_standard]) if case.expected_standard else set()
            relevant_sets.append(relevant)
            t1=time.perf_counter()
            output=pipeline(case)
            latency_ms={"retrieval_ms":(t1-t0)*1000}
            if isinstance(output,dict):
                answer=str(output.get("answer") or output.get("reply") or "")
                records=list(output.get("records") or output.get("source_records") or [])
                resolved_query=output.get("resolved_query")
                context_used=bool(output.get("context_used",False))
                latency_ms.update({k:float(v) for k,v in (output.get("latency_ms") or {}).items()})
            else:
                answer=str(getattr(output,"reply",getattr(output,"answer","")) or "")
                records=list(getattr(output,"source_records",()) or ())
                resolved_query=getattr(output,"resolved_query",None)
                context_used=bool(getattr(output,"context_used",False))
                latency_ms["total_ms"]=float(getattr(output,"execution_ms",0) or 0)
            ev=evaluate_case(case,answer,records,resolved_query=resolved_query,context_used=context_used)
            results.append(CaseResult(case.id,ev["passed"],retrieval={
                kind: _ids(retrievals.get(kind,[])) for kind in ("keyword","vector","hybrid")
            },grounding=ev["grounding"],citation=ev["citation"],version=ev["version"],context=ev["context"],answer_quality=ev["answer_quality"],hallucination=ev["hallucination"],latency_ms=latency_ms))
        except Exception as exc:
            logger.exception("phase15_case_failed case_id=%s",case.id)
            results.append(CaseResult(case.id,False,error=f"{type(exc).__name__}: {exc}"))
    finished=datetime.now(timezone.utc)
    metrics={}
    for kind, rankings in ranking_sets.items():
        if any(relevant_sets):
            metrics[kind]=retrieval_metrics(rankings,relevant_sets,k=5)
    for name, getter in (("grounding","grounding"),("citation","citation"),("version","version"),("context","context"),("answer_quality","answer_quality"),("hallucination","hallucination")):
        vals=[float(r.__dict__[getter].get("grounded_claim_ratio", r.__dict__[getter].get("citation_accuracy", 1.0 if r.__dict__[getter].get("pass") else 0.0))) for r in results if not r.error]
        if vals: metrics[name+"_pass_rate"]=round(sum(1 for r in results if not r.error and r.__dict__[getter].get("pass"))/len(vals),4)
    regression=regression_delta(metrics.get("hybrid",{}),baseline_metrics or {}) if baseline_metrics else {}
    return EvaluationReport(run_id,started.isoformat(),finished.isoformat(),len(cases),sum(1 for r in results if r.passed),sum(1 for r in results if not r.passed),metrics,results,regression,environment)
