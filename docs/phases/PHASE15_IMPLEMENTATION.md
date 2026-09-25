# ManakAi Phase 15 — Advanced AI + Retrieval Evaluation

Phase 15 is observational and regression-focused. It does not mutate BIS
knowledge. The evaluation dataset intentionally stores expected facts only when
they are grounded in the existing project/source contract; clause/amendment
facts are not fabricated.

## Components

- `backend/evaluation/dataset.json` — structured test cases
- `backend/evaluation/metrics.py` — Recall@K, Precision@K, Hit Rate@K, MRR, NDCG
- `backend/evaluation/evaluators.py` — grounding, citations, hallucination,
  version, context and answer-safety checks
- `backend/evaluation/runner.py` — dependency-injected evaluation pipeline
- `backend/evaluation/repository.py` — admin-only persistence
- `database/migrations/0009_phase15_evaluation.sql` — evaluation storage
- `GET /ops/evaluations` and `GET /ops/evaluations/{run_id}` — protected reports

## Important limitation

The included CLI validates the dataset shape but does not invent a live BIS
adapter or silently call production services. Integration/CI should inject the
real Phase 14 pipeline and separate keyword/vector/hybrid retrieval runners.

## Recommended execution

1. Apply migration 0009 after migrations 0001–0008.
2. Run `pytest -q`.
3. In CI, inject the Phase 14 AI1 pipeline into `run_evaluation()`.
4. Persist the resulting report with `save_report()`.
5. Compare hybrid metrics against a checked-in baseline and fail CI when a
   configured metric drops beyond the allowed threshold.

## Security

Evaluation endpoints reuse the existing operations authorization. Evaluation
tables have RLS enabled with no public policies. API keys, passwords and auth
credentials are not part of evaluation logs.
