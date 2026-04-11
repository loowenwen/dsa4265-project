# Backend Guide

Backend for the applicant information processor, model scoring, orchestration, and explanation flow.

## Service Layout
- API routes: `backend/app/api/v1/`
- Schemas: `backend/app/models/`
- Services: `backend/app/services/`
  - Ingestion: `backend/app/services/ingestion/`
    - adapters, normalization, validation, feature-vector pipeline
  - Modeling: `backend/app/services/modeling/`
    - default-risk predictor, anomaly model adapter, provider layer, model exceptions
  - Decisioning: `backend/app/services/decisioning/`
    - rule/AI decision engine, consolidated decision payload builder
  - Explanation: `backend/app/services/explanation/`
    - grounded explanation generation and validation
  - Policy: `backend/app/services/policy/`
    - policy RAG pipeline and policy chunk data
  - Chat: `backend/app/services/chat/`
    - policy retrieval, OpenRouter generation, and in-memory session context

## Backward Compatibility
- Legacy flat import paths under `backend/app/services/*.py` remain as thin wrappers.
- New code should import from the sectioned packages (`ingestion`, `modeling`, `decisioning`, `explanation`, `policy`).

## LLM Explanation
- Set `OPENROUTER_API_KEY` to enable model-generated explanations.
- Optional env var: `EXPLANATION_MODEL` (default from `app/core/settings.py`).
- Explanation generation is grounded by decision payload values and source labels.
- On missing key/invalid output/hallucinated metrics, the API returns `Explanation unavailable`.

## Chat API (MVP)
- Endpoint: `POST /api/v1/chat`
- Request: `message` (required), optional `session_id`, optional `decision_payload`.
- Response: `session_id`, `answer`, `citations`, `llm_used`, and memory summary.
- Memory is in-process only (TTL + turn cap), intended for MVP session continuity.
