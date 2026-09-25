# Phase 6 — AI #1

Implemented a grounded AI explanation pipeline:

User -> FAQ -> cache -> BIS retrieval -> selected context -> Gemini AI #1 -> answer

Key properties:
- Trusted FAQ matches remain a fast path and do not invoke Gemini.
- Non-FAQ questions use the Phase 5 BIS retriever before AI.
- Only top relevant standard records are sent to the model.
- Grounding rules live in `backend/app/services/ai/prompts.py`.
- Gemini/key fallback is isolated in `backend/app/services/ai/llm_service.py`.
- Structured AI results live in `answer_generator.py` and include grounding/provider/fallback state.
- Public `POST /chat` remains `{ "reply": "..." }`.
- No AI #2 was added.
- Provider failures and quota exhaustion use safe public fallbacks.
- Empty retrieval context returns the required reliable-information fallback without calling the model.
- Backend `.env.example` contains placeholders only.

Verification:
`python -m pytest backend/tests -q` -> 32 passed.
