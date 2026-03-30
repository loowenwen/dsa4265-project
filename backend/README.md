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
