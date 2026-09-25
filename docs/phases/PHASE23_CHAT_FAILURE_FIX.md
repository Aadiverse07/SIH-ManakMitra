# Phase 23 Chat Failure Fix

This patch preserves the existing ManakMitra Phase 23 architecture and UI while fixing the failure path observed in the backend logs.

## Root cause addressed

The version-constraining layer could return an empty evidence set when retrieval found multiple standard versions but no authoritative current-version marker. `AI1Pipeline` then passed an empty record list to AI #1. The grounded answer generator correctly refused to call the model with no evidence, producing `provider=not_called`, which immediately forced the request into AI #2.

The patch now preserves the retrieved candidates for these **unresolved version** cases. AI #1 receives the evidence and the existing grounded system prompt requires it to keep versions separate and explicitly state when the requested version cannot be authoritatively resolved.

Exact version requests and source-authoritatively resolved versions remain strict and unchanged.

## Provider robustness addressed

The Gemini client now:

- removes duplicate API keys before attempting provider calls;
- uses a bounded 30-second HTTP timeout by default;
- retries transient provider/transport failures once by default;
- logs only sanitized provider status/type information (never API keys or prompts);
- continues to another configured credential after a failed provider attempt;
- retains the existing quota classification and safe public error behavior.

These changes do **not** change the UI, database schema, BIS retrieval contract, response format, or per-request AI call budget.

## Configuration

Optional settings:

```env
LLM_REQUEST_TIMEOUT_MS=30000
LLM_TRANSIENT_RETRIES=1
```

Existing environments can omit them and receive these defaults.

## Validation

Python syntax compilation passed for all modified Python files. Full pytest execution could not be completed in the build environment because the required `supabase` Python package was not installed and external package installation was unavailable.
