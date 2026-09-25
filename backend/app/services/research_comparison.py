"""Phase 25 — evidence-backed BIS standards comparison engine.

The comparator is deterministic and fail-closed: it only reports a common
requirement, difference, or unique requirement when source evidence for the
relevant standard/version is present. Missing evidence is represented as an
explicit insufficiency rather than filled from model knowledge.
"""
from __future__ import annotations
import re
from typing import Any

from backend.app.services.provenance.evidence_engine import retrieve_evidence
from backend.app.services.retriever import search_bis
from backend.app.services.provenance.service import _build_citation_pairs

CATEGORIES = [
    "scope", "applicability", "definitions", "requirements", "materials",
    "testing", "sampling", "acceptance criteria", "formulas", "tables",
    "certification requirements", "references", "amendments", "version status",
]

_CATEGORY_TERMS = {
    "scope": ("scope", "covers", "applicable to", "this standard specifies"),
    "applicability": ("applicable", "application", "shall apply", "applies to"),
    "definitions": ("definition", "defined as", "means", "terminology"),
    "requirements": ("shall", "requirement", "requirements", "provision", "criteria"),
    "materials": ("material", "materials", "cement", "steel", "aggregate", "ingredient"),
    "testing": ("test", "testing", "test method", "laboratory", "specimen"),
    "sampling": ("sampling", "sample", "lot", "sampling plan"),
    "acceptance criteria": ("acceptance", "acceptance criteria", "conforming", "rejection"),
    "formulas": ("formula", "equation", "calculated", "calculation", "coefficient", "factor"),
    "tables": ("table", "tabulated", "table "),
    "certification requirements": ("certification", "certified", "licence", "license", "marking", "scheme"),
    "references": ("reference", "refer to", "referenced", "normative reference"),
    "amendments": ("amendment", "amended", "corrigendum"),
    "version status": ("current", "superseded", "withdrawn", "active", "edition", "revision", "version"),
}

def extract_standard_refs(text: str) -> list[str]:
    refs = re.findall(r"\bIS\s*[0-9]{1,6}(?:\s*\([^)]*\))?\s*:\s*\d{4}\b", text or "", flags=re.I)
    return list(dict.fromkeys(re.sub(r"\s+", " ", x).upper() for x in refs))

def _contains_target(record: dict[str, Any], target: str) -> bool:
    target = target.upper().replace(" ", "")
    for key in ("number", "standard_number", "is_number", "version", "document_version"):
        value = str(record.get(key) or "").upper().replace(" ", "")
        if target in value:
            return True
    return False

def _category_for(text: str) -> list[str]:
    low = text.lower()
    out=[]
    for category, terms in _CATEGORY_TERMS.items():
        if any(term in low for term in terms): out.append(category)
    return out or ["requirements"]

def _evidence_text(record: dict[str, Any]) -> str:
    return str(record.get("content") or record.get("description") or record.get("desc") or record.get("text_content") or "").strip()

def _short(text: str, n: int=500) -> str:
    text=re.sub(r"\s+", " ", text).strip()
    return text if len(text)<=n else text[:n].rstrip()+"…"

def _norm_fact(text: str) -> str:
    return re.sub(r"[^a-z0-9%./+-]+", " ", text.lower()).strip()

def _records_for_target(records: list[dict[str, Any]], target: str) -> list[dict[str, Any]]:
    exact=[r for r in records if _contains_target(r,target)]
    return exact

def _category_records(records: list[dict[str, Any]], category: str) -> list[dict[str, Any]]:
    return [r for r in records if category in _category_for(_evidence_text(r))]

def _cell(records: list[dict[str, Any]], citations_by_id: dict[str, Any]) -> dict[str, Any]:
    if not records:
        return {"status":"insufficient_evidence", "statements":[], "evidence":[]}
    statements=[]; evidence=[]
    seen=set()
    for r in records[:5]:
        text=_evidence_text(r)
        cid=str((r.get("_citation") or "").strip())
        key=_norm_fact(text)
        if not text or key in seen: continue
        seen.add(key)
        statements.append(_short(text))
        if cid in citations_by_id:
            evidence.append(cid)
    return {"status":"evidence_found", "statements":statements, "evidence":evidence}

def compare_standards(question: str, targets: list[str], all_records: list[dict[str, Any]]) -> dict[str, Any]:
    targets=list(dict.fromkeys(targets))
    if len(targets)!=2:
        return {"status":"insufficient_evidence", "message":"Exactly two identifiable BIS standard/version references are required for a structured comparison.", "targets":targets, "categories":[], "common_requirements":[], "differences":[], "unique_requirements":[], "testing_differences":[], "version_differences":[], "evidence":[]}

    per_target={t:_records_for_target(all_records,t) for t in targets}
    pairs = _build_citation_pairs(all_records)
    citations = [c for _, c in pairs]
    citations_by_id={c.citation_id:c for c in citations}
    for r,c in pairs:
        r["_citation"]=c.citation_id
    paired_ids={id(r) for r,_ in pairs}
    for t in targets:
        per_target[t][:] = [r for r in per_target[t] if id(r) in paired_ids]

    rows=[]; differences=[]; common=[]; unique=[]
    for category in CATEGORIES:
        a=_cell(_category_records(per_target[targets[0]],category), citations_by_id)
        b=_cell(_category_records(per_target[targets[1]],category), citations_by_id)
        row={"category":category,"standard_a":a,"standard_b":b}
        rows.append(row)
        if a["status"]=="evidence_found" and b["status"]=="evidence_found":
            af={_norm_fact(x) for x in a["statements"]}; bf={_norm_fact(x) for x in b["statements"]}
            if af == bf:
                common.append({"category":category,"evidence":sorted(set(a["evidence"]+b["evidence"]))})
            else:
                differences.append({"category":category,"standard_a":a,"standard_b":b})
        elif a["status"]=="evidence_found" and b["status"]!="evidence_found":
            unique.append({"category":category,"standard":targets[0],"evidence":a})
        elif b["status"]=="evidence_found" and a["status"]!="evidence_found":
            unique.append({"category":category,"standard":targets[1],"evidence":b})

    testing_differences=[d for d in differences if d["category"] in {"testing","sampling","acceptance criteria"}]
    version_differences=[d for d in differences if d["category"] in {"version status","amendments"}]
    evidence_register=[]
    for c in citations:
        evidence_register.append({"citation_id":c.citation_id,"standard_number":c.standard_number,"clause":c.clause,"page":c.page,"source":c.source_authority,"source_url":c.source_url,"evidence_text":_short(c.evidence_text or "",800)})

    return {"status":"completed" if citations else "insufficient_evidence", "targets":targets, "categories":rows, "common_requirements":common, "differences":differences, "unique_requirements":unique, "testing_differences":testing_differences, "version_differences":version_differences, "evidence":evidence_register}

def _fmt_cell(cell: dict[str, Any]) -> str:
    if cell.get("status") != "evidence_found":
        return "Insufficient evidence"
    parts = []
    for i, stmt in enumerate(cell.get("statements", [])):
        cid = cell.get("evidence", [])[i] if i < len(cell.get("evidence", [])) else None
        # A literal "|" (common in OCR'd tables) would split the Markdown cell.
        stmt = str(stmt).replace("|", "\\|")
        parts.append(f"{stmt} [{cid}]" if cid else stmt)
    return "<br>".join(parts) if parts else "Insufficient evidence"

def render_comparison_report(question: str, comparison: dict[str, Any]) -> str:
    """Render the structured comparison as a Markdown report.

    This is the only place a comparison's ``report`` text is produced. It is
    built entirely from the already-computed, evidence-gated ``comparison``
    dict — no new facts are introduced here.
    """
    targets = comparison.get("targets") or ["Standard A", "Standard B"]
    a_label = targets[0] if len(targets) > 0 else "Standard A"
    b_label = targets[1] if len(targets) > 1 else "Standard B"

    if comparison.get("status") != "completed":
        message = comparison.get("message") or "Insufficient source-backed evidence was found to produce a structured comparison."
        return (
            "## Executive Summary\n\n" + message + "\n\n"
            "## Limitations\n\nThe Research Centre does not substitute general model knowledge for BIS evidence. "
            "Provide two clearly identifiable BIS standard/version references (e.g. `IS 456:2000`) to run a structured comparison."
        )

    table_rows = "\n".join(
        f"| {row['category']} | {_fmt_cell(row['standard_a'])} | {_fmt_cell(row['standard_b'])} |"
        for row in comparison.get("categories", [])
    )
    table = f"| Category | {a_label} | {b_label} |\n| --- | --- | --- |\n{table_rows}"

    def _list_or_none(items: list[str]) -> str:
        return "\n".join(f"- {x}" for x in items) if items else "- None established from the retrieved evidence."

    common = _list_or_none([f"{c['category']} — evidence agrees between the two sources. [{', '.join(c['evidence'])}]" for c in comparison.get("common_requirements", [])])
    differences = _list_or_none([f"{d['category']} — evidence differs between {a_label} and {b_label}." for d in comparison.get("differences", [])])
    unique = _list_or_none([f"{u['category']} — evidence found only for {u['standard']}." for u in comparison.get("unique_requirements", [])])
    testing_diff = _list_or_none([f"{d['category']} — evidence differs between {a_label} and {b_label}." for d in comparison.get("testing_differences", [])])
    version_diff = _list_or_none([f"{d['category']} — evidence differs between {a_label} and {b_label}." for d in comparison.get("version_differences", [])])
    evidence = "\n".join(
        f"- [{e['citation_id']}] {e.get('standard_number') or 'Unknown standard'}"
        + (f", clause {e['clause']}" if e.get("clause") else "")
        + (f", page {e['page']}" if e.get("page") else "")
        + f": {e.get('evidence_text') or ''}"
        for e in comparison.get("evidence", [])
    ) or "- No evidence-backed citations were produced."

    return (
        f"## Executive Summary\n\nStructured, evidence-backed comparison of {a_label} and {b_label} across "
        f"{len(comparison.get('categories', []))} categories. Only categories with retrieved evidence for both, "
        "one, or either standard are reported as common, different, or unique — missing evidence is never treated as a difference.\n\n"
        f"## Structured Comparison\n\n{table}\n\n"
        f"## Common Requirements\n\n{common}\n\n"
        f"## Differences\n\n{differences}\n\n"
        f"## Unique Requirements\n\n{unique}\n\n"
        f"## Testing Differences\n\n{testing_diff}\n\n"
        f"## Version Differences\n\n{version_diff}\n\n"
        f"## Evidence\n\n{evidence}\n\n"
        "## Methodology\n\nEvidence retrieval followed the existing BIS retrieval/provenance layers; general model knowledge was not used as authority.\n\n"
        "## Limitations\n\nA missing category is not treated as proof that a standard has no requirement. "
        "Differences are asserted only where comparable, source-backed evidence exists for both standards."
    )

def run_comparison(question: str, targets: list[str], user_id: str) -> dict[str, Any]:
    merged=[]; seen=set()
    for target in targets:
        records=retrieve_evidence(target, base_retrieval=lambda q, category=None, top_k=10: search_bis(q, top_k=top_k), top_k=14, user_id=user_id)
        for r in records:
            key=str(r.get("knowledge_id") or r.get("evidence_id") or r.get("id") or (r.get("number"),r.get("content")))
            if key not in seen:
                seen.add(key); merged.append(r)
    comparison=compare_standards(question, targets, merged)
    report=render_comparison_report(question, comparison)
    has_signal = bool(comparison.get("evidence")) and (
        len(comparison.get("differences", [])) + len(comparison.get("common_requirements", [])) + len(comparison.get("unique_requirements", [])) > 0
    )
    return {"question":question,"research_type":"STANDARDS_COMPARISON","report":report,"comparison":comparison,"evidence":comparison.get("evidence",[]),"citations":comparison.get("evidence",[]),"confidence":"moderate" if has_signal else "insufficient","limitations":["Only retrieved source-backed evidence is compared.","A missing category is not treated as proof that the standard has no requirement.","Differences are not asserted where comparable evidence is unavailable."],"workflow":[] }
