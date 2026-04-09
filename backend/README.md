# Backend Guide

This backend currently focuses on the Applicant Information Processor module.

## Where to add your code
- API routes: `backend/app/api/v1/`
- Schemas: `backend/app/models/`
- Processing logic: `backend/app/services/`
  - adapters: `backend/app/services/adapters/`
  - normalizer: `backend/app/services/normalizer.py`
  - validator: `backend/app/services/validator.py`
  - enricher: `backend/app/services/enricher.py`
  - pipeline: `backend/app/services/pipeline.py`
- Tests: `backend/tests/`

## LLM explanation agent
- Set `OPENAI_API_KEY` in your environment before starting the backend.
- Optional: set `EXPLANATION_MODEL` to override the default model `gpt-4o-mini`.
- The explanation endpoint keeps the orchestrator as the decision source of truth.
- The LLM only generates the natural-language explanation paragraph.
- If the LLM response is missing, invalid, or introduces unsupported claims, the backend automatically falls back to the deterministic explainer.
