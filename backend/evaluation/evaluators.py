from __future__ import annotations
import re
from typing import Any
from backend.app.services.provenance.service import build_citations, extract_citation_ids, validate_citations

_STANDARD_RE=re.compile(r"\bIS\s+\d{1,6}(?:\s*\([^)]*\))?\s*:\s*\d{4}\b",re.I)
_CLAUSE_RE=re.compile(r"\b(?:clause|section)\s+(\d+(?:\.\d+)+)\b",re.I)
_YEAR_RE=re.compile(r"\b(?:19|20)\d{2}\b")

def _text(record:dict[str,Any])->str:
    vals=[]
    for k in ("number","title","desc","description","content","clause","subclause","source","source_url","version_label","document_version","amendment_label"):
        if record.get(k) is not None: vals.append(str(record[k]))
    return " ".join(vals)

def _supported_tokens(answer:str, records:list[dict[str,Any]])->set[str]:
    corpus=" ".join(_text(r) for r in records).lower()
    return {x.lower() for x in re.findall(r"[a-z0-9]+",answer or "") if len(x)>=4 and x.lower() in corpus}

def evaluate_grounding(question:str, answer:str, records:list[dict[str,Any]])->dict:
    a=(answer or "").strip()
    if not a: return {"grounded_claim_ratio":0.0,"unsupported_claim_ratio":1.0,"evidence_relevance":0.0,"pass":False,"issues":["empty answer"]}
    supported=_supported_tokens(a,records)
    claims=[s.strip() for s in re.split(r"(?<=[.!?])\s+",a) if s.strip()]
    if not claims:
        claims=[a]
    claim_scores=[]
    for claim in claims:
        tokens=[x.lower() for x in re.findall(r"[a-z0-9]+",claim) if len(x)>=4]
        overlap=len(set(tokens)&supported)/max(1,len(set(tokens)))
        claim_scores.append(overlap)
    ratio=sum(1 for s in claim_scores if s>=0.20)/len(claim_scores)
    standard_mentions=_STANDARD_RE.findall(a)
    known_standards={str(r.get("number") or r.get("is_number") or "").lower().replace(" ","") for r in records}
    bad_standard=[x for x in standard_mentions if x.lower().replace(" ","") not in known_standards]
    clause_mentions=_CLAUSE_RE.findall(a)
    known_clauses={str(r.get("clause") or r.get("clause_number") or "") for r in records}
    bad_clauses=[x for x in clause_mentions if x not in known_clauses] if clause_mentions and known_clauses else []
    issues=[]
    if bad_standard: issues.append("answer mentions standard(s) absent from evidence: "+", ".join(bad_standard))
    if bad_clauses: issues.append("answer mentions clause(s) absent from evidence: "+", ".join(bad_clauses))
    if not records and a:
        issues.append("non-empty answer with no retrieved evidence")
    safe_uncertainty = bool(re.search(r"\b(could not|couldn't|cannot|can't|unable|not verified|insufficient|no reliable)\b", a, re.I))
    passed = (
        (not records and safe_uncertainty)
        or (bool(records) and ratio >= 0.60 and not bad_standard and not bad_clauses)
    )
    return {"grounded_claim_ratio":round(ratio,4),"unsupported_claim_ratio":round(1-ratio,4),"evidence_relevance":round(sum(claim_scores)/len(claim_scores),4),"pass":passed,"issues":issues}

def evaluate_citations(answer:str, records:list[dict[str,Any]])->dict:
    citations=build_citations(records)
    refs=extract_citation_ids(answer)
    validation=validate_citations(citations,refs)
    expected_count=len(citations)
    # Backend-attached footer is valid, but citation completeness is measured
    # conservatively: every cited id must be valid; factual answers with evidence
    # should expose at least one citation.
    accuracy=1.0 if validation.valid else max(0.0,1-len(validation.invalid_ids)/max(1,len(refs)))
    completeness=1.0 if (not records or refs) else 0.0
    source_accuracy=1.0
    version_accuracy=1.0
    clause_accuracy=1.0
    issues=list(validation.issues)
    for c in citations:
        if c.source_url is None and c.source_authority is None:
            source_accuracy=0.0
        if c.clause and not c.evidence_id: clause_accuracy=0.0
        if c.version and c.version_id is None and c.document_version is None:
            version_accuracy=0.0
    return {"citation_accuracy":round(accuracy,4),"citation_completeness":completeness,"citation_validity":1.0 if validation.valid else 0.0,"clause_accuracy":clause_accuracy,"version_accuracy":version_accuracy,"source_accuracy":source_accuracy,"pass":bool(validation.valid and (not records or refs)),"issues":issues,"referenced_ids":refs,"expected_citations":expected_count}

def evaluate_hallucination(answer:str, records:list[dict[str,Any]], case=None)->dict:
    standards=_STANDARD_RE.findall(answer or "")
    evidence_numbers={str(r.get("number") or r.get("is_number") or "").strip().lower() for r in records}
    invented=[s for s in standards if s.strip().lower() not in evidence_numbers]
    clauses=_CLAUSE_RE.findall(answer or "")
    evidence_clauses={str(r.get("clause") or r.get("clause_number") or "").strip() for r in records}
    invented_clauses=[c for c in clauses if evidence_clauses and c not in evidence_clauses]
    # Strongly reject explicit invention requests when the answer complies.
    invention_words=bool(re.search(r"\b(invent|make up|fabricat)\w*\b",answer or "",re.I))
    return {"invented_standards":invented,"invented_clauses":invented_clauses,"unsupported_dates":False,"unsupported_amendments":False,"unsupported_certification_rules":False,"pass":not invented and not invented_clauses and not invention_words,"issues":(["invented standard/clauses detected"] if invented or invented_clauses else [])}

def evaluate_version(case, records:list[dict[str,Any]], answer:str)->dict:
    expected=case.expected_version
    if not expected: return {"pass":True,"version_match":None,"mixed_version":False,"issues":[]}
    labels={str(r.get("version_label") or r.get("number") or r.get("is_number") or "").strip().lower() for r in records}
    mentioned={x.strip().lower() for x in _STANDARD_RE.findall(answer or "")}
    if expected.lower() not in labels:
        return {"pass":False,"version_match":False,"mixed_version":len(labels)>1,"issues":["requested version is absent from retrieved evidence"]}
    wrong=mentioned-{expected.lower()}
    return {"pass":not wrong and len(labels)<=1,"version_match":True,"mixed_version":len(labels)>1,"issues":["answer mentions incompatible version"] if wrong else []}

def evaluate_context(case, resolved_query:str|None, context_used:bool)->dict:
    if "followup" not in case.tags: return {"pass":True,"resolved":None,"context_used":context_used,"issues":[]}
    resolved=bool(resolved_query and resolved_query.strip()!=case.question.strip())
    return {"pass":resolved and context_used,"resolved":resolved,"context_used":context_used,"issues":[] if resolved and context_used else ["follow-up was not resolved from context"]}

def evaluate_answer_quality(case, answer:str, records:list[dict[str,Any]])->dict:
    a=(answer or "").strip()
    insufficient=not records
    safe_markers=bool(re.search(r"\b(could not|couldn't|cannot|can't|not enough|unable to verify|insufficient|don't have reliable|not verified)\b",a,re.I))
    if insufficient:
        passed=safe_markers or not a
        return {"relevance":1.0 if passed else 0.0,"complete":passed,"pass":passed,"issues":[] if passed else ["answer did not acknowledge insufficient evidence"]}
    return {"relevance":1.0 if a else 0.0,"complete":len(a)>=20,"pass":bool(a) and len(a)>=20,"issues":[] if a else ["empty answer"]}

def evaluate_case(case, answer:str, records:list[dict[str,Any]], *, resolved_query=None, context_used=False)->dict:
    evidence_numbers={str(r.get("number") or r.get("is_number") or "").strip().lower() for r in records}
    standard_match = (not case.expected_standard) or (case.expected_standard.strip().lower() in evidence_numbers)
    clause_values={str(r.get("clause") or r.get("clause_number") or "").strip() for r in records}
    clause_match = (not case.expected_clause) or (case.expected_clause.strip() in clause_values)
    expected_evidence={"pass": bool(standard_match and clause_match),
                       "standard_match": standard_match,
                       "clause_match": clause_match,
                       "issues":[]}
    if case.expected_standard and not standard_match:
        expected_evidence["issues"].append("expected standard is absent from retrieved evidence")
    if case.expected_clause and not clause_match:
        expected_evidence["issues"].append("expected clause is absent from retrieved evidence")
    grounding=evaluate_grounding(case.question,answer,records)
    citation=evaluate_citations(answer,records)
    hallucination=evaluate_hallucination(answer,records,case)
    version=evaluate_version(case,records,answer)
    context=evaluate_context(case,resolved_query,context_used)
    quality=evaluate_answer_quality(case,answer,records)
    # If a case has no expected standard/evidence, retrieval can be legitimately empty.
    passed=all(x.get("pass",False) for x in (expected_evidence,grounding,citation,hallucination,version,context,quality))
    return {"passed":passed,"expected_evidence":expected_evidence,"grounding":grounding,"citation":citation,"hallucination":hallucination,"version":version,"context":context,"answer_quality":quality}
