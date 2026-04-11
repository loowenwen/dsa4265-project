# dsa4265-project

## Project Layout
- `backend/`: FastAPI service for ingestion, scoring, orchestration, and explanation.
- `frontend/`: Next.js UI for applicant form submission and decision display.
- `docker-compose.yml`: local full-stack orchestration.

## Backend Service Sections
- `app/services/ingestion/`: form adapters, normalization, validation, pipeline.
- `app/services/modeling/`: default-risk model, anomaly model, provider/readiness logic.
- `app/services/decisioning/`: decision engine and consolidated payload builder.
- `app/services/explanation/`: explanation agent interface/guardrails.
- `app/services/policy/`: policy retrieval/RAG utilities.

Legacy `app/services/*.py` files are compatibility wrappers to preserve existing imports.
