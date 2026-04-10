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
- Set `OPENROUTER_API_KEY` in your environment before starting the backend.
- Optional: set `EXPLANATION_MODEL` to override the default model `google/gemini-2.0-flash-exp:free`.
- The explanation endpoint keeps the orchestrator as the decision source of truth.
- The LLM only generates the explanation summary plus supporting and cautionary evidence.
- If the LLM response is missing, invalid, or introduces unsupported claims, the backend returns `Explanation unavailable`.
