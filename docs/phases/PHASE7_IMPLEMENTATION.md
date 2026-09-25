# Phase 7 — AI #1 → AI #2 Fallback

Implemented flow:

```text
User
  ↓
FAQ / cache
  ↓
BIS retrieval
  ↓
AI #1
  ↓
Structured local evaluation
  ├── solved → FINAL RESPONSE
  └── not solved → AI #2 → FINAL RESPONSE
```

## AI #1 evaluation

`backend/app/services/ai/evaluation.py` defines the typed `AI1Evaluation` contract:

- `understood`
- `sufficient_context`
- `grounded`
- `complete_enough`
- `confidence`
- `reason`

The fallback decision is deterministic and local. It does not spend another
LLM call to judge AI #1. AI #2 runs when any required evaluation condition
fails or confidence is below the configured threshold (`0.75`).

The grounding check is deliberately conservative: AI #1 must have usable
retrieved context, a successful provider result, the expected grounding state,
and an identifying term from the selected standard number/title.

## AI #2

`backend/app/services/ai/fallback.py` is lazy: its provider service is created
only when fallback is actually triggered.

AI #2 can reason about complex or ambiguous questions, but its system policy
requires it to distinguish:

- verified BIS information present in `official_verified` records
- general explanation
- unverified/uncertain information

It must not invent official BIS numbers, requirements, fees, procedures,
statuses, dates, or other authoritative details.

Optional dedicated AI #2 credentials/model can be configured with:

```text
AI2_API_KEY=
AI2_API_KEY_2=
AI2_API_KEY_3=
AI2_API_KEY_4=
AI2_MODEL=gemini-3.6-flash
```

If dedicated AI #2 keys are not supplied, the configured AI #1 keys are reused
only when the fallback path actually executes.

## Logging

Phase 7 logs internal outcome metadata:

- AI #1 provider status
- evaluation confidence/grounding/completeness
- whether fallback triggered
- AI #1 execution time
- AI #2 provider status
- AI #2 execution time
- whether an error occurred

Question text, answers, API keys, and provider exception details are not logged.

## API compatibility

`POST /chat` remains:

```json
{
  "reply": "..."
}
```

No frontend API contract change was required.

## Tests

Added `backend/tests/test_phase7_fallback.py` covering:

1. AI #1 solves → AI #2 not called.
2. AI #1 fails → AI #2 called.
3. Low confidence → AI #2 called.
4. AI #2 fails → graceful safe response.
5. Both fail → safe response without provider error leakage.

Phase 1–7 backend test suite result in the development verification environment:

`37 passed`
