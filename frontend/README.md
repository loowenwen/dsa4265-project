# Applicant Information Processor (v1)

Minimal full-stack v1 for normalizing applicant form input into a structured feature vector.

## Stack
- Frontend: Next.js + React + Tailwind CSS
- Backend: FastAPI
- Local dev/deployment: Docker + Docker Compose

## Features in v1
- Form-first input with required fields:
  - `annual_income`
  - `loan_amount`
  - `debt_to_income_ratio`
  - `recent_delinquencies`
  - `employment_length_months`
- Optional `additional_information` text field.
- Strict validation:
  - Missing/malformed required fields return `422` with field-level errors.
- Normalized structured output with:
  - `feature_vector`
  - `normalized_fields`
  - `missing_fields`
  - `suspicious_fields`

## Project Structure
```text
backend/
  app/
    api/v1/
    models/
    services/
      adapters/
  tests/
frontend/
  app/
    components/
  lib/
  types/
docker-compose.yml
```

## Run with Docker Compose
```bash
docker compose up --build
```

Services:
- Frontend: http://localhost:3000
- Backend API docs: http://localhost:8000/docs

## Backend API
### Health check
- `GET /api/v1/health`

### Process applicant
- `POST /api/v1/process`

Example request:
```json
{
  "annual_income": "$42,000",
  "loan_amount": "18000",
  "debt_to_income_ratio": "46%",
  "recent_delinquencies": "2",
  "employment_length_months": "8 months",
  "additional_information": "Applicant Summary: no additional demographic details."
}
```

Example response:
```json
{
  "feature_vector": {
    "annual_income": 42000.0,
    "loan_amount": 18000.0,
    "debt_to_income_ratio": 46.0,
    "recent_delinquencies": 2,
    "employment_length_months": 8,
    "demographic_information": "cannot identify"
  },
  "normalized_fields": {
    "annual_income": {
      "value": 42000.0,
      "status": "identified",
      "source_text": "$42,000"
    },
    "loan_amount": {
      "value": 18000.0,
      "status": "identified",
      "source_text": "18000"
    },
    "debt_to_income_ratio": {
      "value": 46.0,
      "status": "identified",
      "source_text": "46%"
    },
    "recent_delinquencies": {
      "value": 2,
      "status": "identified",
      "source_text": "2"
    },
    "employment_length_months": {
      "value": 8,
      "status": "identified",
      "source_text": "8 months"
    },
    "demographic_information": {
      "value": "cannot identify",
      "status": "cannot_identify",
      "source_text": null
    }
  },
  "missing_fields": ["demographic_information"],
  "suspicious_fields": [
    {
      "field": "debt_to_income_ratio",
      "reason": "DTI above 43%",
      "severity": "medium"
    }
  ]
}
```

## Local Backend Tests
Run from repo root:
```bash
cd backend && python3 -m unittest discover -s tests -v
```


# Frontend Guide


## Where to add your code
- Pages/routes: `frontend/app/`
- Components: `frontend/app/components/`
- API calls: `frontend/lib/`
- Types: `frontend/types/`
