import math

def test_phase15_retrieval_metrics():
    from backend.evaluation.metrics import retrieval_metrics, regression_delta
    m=retrieval_metrics([["A","B","C"],["B","A"]],[{"A"},{"A"}],k=3)
    assert m["recall@3"] == 1.0
    assert m["mrr"] == 0.75
    assert regression_delta({"recall@5":0.70},{"recall@5":0.90})["has_regression"]

def test_phase15_dataset_is_source_conservative():
    from backend.evaluation.runner import load_dataset
    cases=load_dataset()
    assert len(cases) >= 10
    clause=next(c for c in cases if c.id=="bis_clause_001")
    assert clause.expected_clause=="7.2"
    assert clause.expected_source is None

def test_phase15_hallucination_and_insufficient_evidence():
    from backend.evaluation.evaluators import evaluate_case
    from backend.evaluation.models import EvaluationCase
    case=EvaluationCase(id="x",question="What rule applies?",tags=("no-answer",))
    result=evaluate_case(case,"I could not verify a reliable BIS requirement from the available evidence.",[])
    assert result["passed"]
    bad=evaluate_case(case,"IS 99999:2099 requires this.",[])
    assert not bad["passed"]

def test_phase15_citation_validation_rejects_unknown_ids():
    from backend.evaluation.evaluators import evaluate_citations
    records=[{"number":"IS 456:2000","title":"Plain and Reinforced Concrete","source":"BIS","source_url":"https://www.services.bis.gov.in/","evidence_id":"e1"}]
    result=evaluate_citations("Answer [C99]",records)
    assert not result["pass"]
    assert "C99" in result["referenced_ids"]

def test_phase15_context_case_requires_resolution():
    from backend.evaluation.evaluators import evaluate_context
    from backend.evaluation.models import EvaluationCase
    c=EvaluationCase(id="f",question="What about testing?",tags=("followup",))
    assert evaluate_context(c,"IS 456:2000 testing",True)["pass"]
    assert not evaluate_context(c,None,False)["pass"]

def test_phase15_expected_standard_and_clause_are_enforced():
    from backend.evaluation.evaluators import evaluate_case
    from backend.evaluation.models import EvaluationCase
    c=EvaluationCase(id="c",question="What does clause 7.2 of IS 456:2000 require?",expected_standard="IS 456:2000",expected_clause="7.2")
    records=[{"number":"IS 456:2000","title":"Plain and Reinforced Concrete","clause":"7.1","evidence_id":"e1","source":"BIS","source_url":"https://www.services.bis.gov.in/"}]
    result=evaluate_case(c,"The evidence does not contain the requested clause.",records)
    assert not result["passed"]
    assert not result["expected_evidence"]["clause_match"]
