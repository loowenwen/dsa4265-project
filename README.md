# Intelligent Credit Underwriting System

This repository contains an end-to-end financial AI course project for intelligent credit underwriting. It combines applicant ingestion, validation, default-risk scoring, anomaly detection, decision orchestration, explanation generation, policy retrieval, and a policy chatbot behind a FastAPI backend and a Next.js frontend.

## What the Project Does

The system is designed as a local prototype for credit underwriting workflows: a user submits applicant information, the backend scores and checks the application, and the frontend displays the decision evidence in a form suitable for review and explanation.

- Accepts applicant records through a web form or sample file upload.
- Normalizes and validates fields required by the credit-risk model.
- Runs a bundled LightGBM-style default-risk model artifact.
- Runs a bundled PyTorch autoencoder anomaly detector.
- Applies rule-based decision logic and, when configured, an optional OpenRouter LLM decision path.
- Builds a consolidated decision payload for downstream explanation.
- Generates grounded explanations when `OPENROUTER_API_KEY` is available, with a deterministic unavailable response when it is not.
- Provides a policy chatbot with short-term in-memory session history and retrieval-backed fallback answers.
- Exposes the workflow through a Next.js UI.

## System Architecture

The project has two main services:

- `backend/`: FastAPI service. It owns ingestion, validation, model providers, decisioning, explanation generation, policy retrieval, and chatbot orchestration.
- `frontend/`: Next.js application. It owns the applicant workflow, result display, explanation display, diagnostics, and chat widget.

The backend loads local model artifacts from `backend/app/models/` by default. External LLM calls are optional and are routed through OpenRouter when configured. The policy chatbot uses a lightweight local retrieval fallback in its fast path, so it can still return policy-grounded text when external LLM generation is unavailable.

`docker-compose.yml` can run the backend and frontend together for local development.

## Repository Structure

```text
dsa4265-project/
  README.md
  requirements.txt
  docker-compose.yml
  backend/
    Dockerfile
    requirements.txt
    app/
      main.py                         FastAPI application entrypoint
      api/v1/                         /process, /explain, /chat, /health routes
      core/                           settings and decision thresholds
      models/                         Pydantic schemas and bundled model artifacts
      services/
        ingestion/                    adapters, normalization, validation, pipeline
        modeling/                     default-risk model, anomaly model, providers
        decisioning/                  rule/AI decision engine and payload builder
        explanation/                  OpenRouter explanation interface and guardrails
        policy/                       local policy retrieval/RAG utilities
        chat/                         policy chatbot and short-term memory
    chroma_underwriting_policy_db/    persisted local policy retrieval index
    tests/                            backend unit/API tests
  frontend/
    Dockerfile
    package.json
    package-lock.json
    app/                              Next.js pages and components
    lib/                              API client, form state, file parsing helpers
    public/samples/                   sample applicant files
    types/                            frontend API types
```

Legacy files under `backend/app/services/*.py` are compatibility wrappers for older imports. The active implementations are in the service subdirectories listed above.

## Prerequisites

- Python 3.11 is recommended. The backend Docker image uses Python 3.11.
- Node.js 20 is recommended. The frontend Docker image uses Node 20.
- npm, for frontend dependency installation.
- Docker and Docker Compose, optional but supported for full-stack local development.

On macOS/Linux, the commands below assume a POSIX shell such as `zsh` or `bash`.

## Environment Variables

Most features run locally without API keys. OpenRouter-backed explanation, chat generation, and optional AI decisioning require `OPENROUTER_API_KEY`.

| Variable | Required | Used by | Purpose | Example |
| --- | --- | --- | --- | --- |
| `OPENROUTER_API_KEY` | Optional | Backend | Enables LLM explanation, chatbot generation, and optional AI decision call. Without it, deterministic fallback behavior is used. | `sk-or-v1-...` |
| `OPENROUTER_BASE_URL` | Optional | Backend | OpenRouter chat-completions endpoint. | `https://openrouter.ai/api/v1/chat/completions` |
| `OPENROUTER_MODEL` | Optional | Backend decision engine | Model for the optional AI decision path. | `nvidia/nemotron-3-super-120b-a12b:free` |
| `EXPLANATION_MODEL` | Optional | Backend explanation service | Model for `/api/v1/explain`. | `openai/gpt-oss-120b:free` |
| `EXPLANATION_TIMEOUT_SECONDS` | Optional | Backend explanation service | Timeout for explanation LLM calls. | `20` |
| `CHAT_MODEL` | Optional | Backend chat service | Model for `/api/v1/chat`. | `openai/gpt-oss-120b:free` |
| `CHAT_TIMEOUT_SECONDS` | Optional | Backend chat service | Timeout for chat LLM calls. | `20` |
| `CHAT_MEMORY_MAX_TURNS` | Optional | Backend chat service | Maximum remembered chat turns per session. | `6` |
| `CHAT_MEMORY_TTL_SECONDS` | Optional | Backend chat service | Chat session memory lifetime in seconds. | `1800` |
| `OPENROUTER_HTTP_REFERER` | Optional | Backend | HTTP referer header sent to OpenRouter. | `http://localhost` |
| `OPENROUTER_APP_TITLE` | Optional | Backend | App title header sent to OpenRouter. | `credit-risk-explainer` |
| `CREDIT_MODEL_PATH` | Optional | Backend model provider | Override default-risk model artifact path. Relative paths are resolved from `backend/` when running the backend commands below. | `app/models/credit_risk_lgbm.joblib` |
| `ANOMALY_MODEL_DIR` | Optional | Backend model provider | Override anomaly model artifact directory. | `app/models/ae_agent` |
| `ANOMALY_MODEL_DEVICE` | Optional | Backend anomaly model | Torch device for anomaly scoring. | `cpu` |
| `NEXT_PUBLIC_API_BASE_URL` | Optional | Frontend | Backend URL used by browser-side frontend API calls. Code defaults to `http://localhost:8000`. | `http://localhost:8000` |
| `OPENAI_API_KEY` | Optional/currently unused | Backend settings | Present in settings for future provider support. | `sk-...` |
| `OPENAI_BASE_URL` | Optional/currently unused | Backend settings | OpenAI-compatible base URL for future provider support. | `https://api.openai.com/v1` |
| `GEMINI_API_KEY` | Optional/currently unused | Backend settings | Present in settings for future provider support. | `...` |
| `GEMINI_BASE_URL` | Optional/currently unused | Backend settings | Gemini base URL for future provider support. | `https://generativelanguage.googleapis.com/v1beta` |

See `.env.example` for a copyable starting point. For local shell runs, export the variables in your terminal. For Docker Compose, copy `.env.example` to `.env`; Compose reads `.env` from the repository root.

## Quick Start

### 1. Clone repo

```bash
git clone <repo-url>
cd dsa4265-project
```

### 2. Create and activate Python virtual environment

```bash
python3.11 -m venv .venv
source .venv/bin/activate
```

If `python3.11` is not available but Python 3.11 is your default Python, use:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Install Python dependencies

From the repository root:

```bash
python -m pip install --upgrade pip
pip install -r requirements.txt
```

`requirements.txt` mirrors the backend runtime dependencies in `backend/requirements.txt`.

### 4. Install frontend dependencies

```bash
cd frontend
npm install
cd ..
```

The repo includes `frontend/package-lock.json`, so `npm ci` is also suitable for a clean reproducible install.

### 5. Configure environment variables

For the basic local demo, no API key is required. To enable LLM explanation and chat generation:

```bash
export OPENROUTER_API_KEY="<your-openrouter-api-key>"
```

Optional frontend override:

```bash
cd frontend
printf "NEXT_PUBLIC_API_BASE_URL=http://localhost:8000\n" > .env.local
cd ..
```

The frontend already defaults to `http://localhost:8000`, so this file is only needed if your backend runs elsewhere.

### 6. Run backend

Open one terminal:

```bash
source .venv/bin/activate
cd backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Backend URLs:

- API docs: <http://localhost:8000/docs>
- Health check: <http://localhost:8000/api/v1/health>
- Model readiness: <http://localhost:8000/api/v1/health/models>

### 7. Run frontend

Open a second terminal:

```bash
cd frontend
npm run dev
```

### 8. Open the website

Open <http://localhost:3000> in your browser.

## Running with Docker Compose

The repository includes `docker-compose.yml` with backend and frontend services.

```bash
cp .env.example .env
# Edit .env if you want to add OPENROUTER_API_KEY or override model settings.
docker compose up --build
```

Services:

- Frontend: <http://localhost:3000>
- Backend API docs: <http://localhost:8000/docs>
- Backend health: <http://localhost:8000/api/v1/health>

Notes:

- Compose mounts `./backend:/app`, so the bundled model artifacts under `backend/app/models/` are available inside the backend container.
- The frontend container sets `NEXT_PUBLIC_API_BASE_URL=http://localhost:8000`, which is correct for browser-side calls from your machine.
- Running the backend Dockerfile by itself without the Compose volume may omit local model artifacts because the Dockerfile copies `app/` only. Prefer Compose for the full-stack local workflow.

## Backend Notes

FastAPI app entrypoint:

```text
backend/app/main.py
```

Main routes:

- `GET /api/v1/health`
- `GET /api/v1/health/models`
- `POST /api/v1/process`
- `POST /api/v1/explain`
- `POST /api/v1/chat`

The `/api/v1/process` endpoint expects the model-aligned applicant schema:

```json
{
  "person_age": "29",
  "person_income": "42000",
  "person_home_ownership": "RENT",
  "person_emp_length": "1 year",
  "loan_intent": "PERSONAL",
  "loan_grade": "D",
  "loan_amnt": "18000",
  "loan_int_rate": "15.5%",
  "loan_percent_income": "46%",
  "cb_person_default_on_file": "N",
  "cb_person_cred_hist_length": "4"
}
```

Run backend tests from the repository root after installing dependencies:

```bash
source .venv/bin/activate
cd backend
python -m unittest discover -s tests -v
```

## Frontend Notes

Next.js app location:

```text
frontend/app/
```

Frontend API client:

```text
frontend/lib/api.ts
```

The frontend uses these package scripts:

- `npm run dev`: local development server.
- `npm run build`: production build.
- `npm run start`: start a production build.
- `npm run lint`: Next.js lint command.

Default local URL:

```text
http://localhost:3000
```

Sample applicant files are available in `frontend/public/samples/`.

## How to Run the Website Locally

Use these line-by-line instructions for a clean setup:

```bash
cd dsa4265-project
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
cd frontend
npm install
cd ..
```

Terminal 1:

```bash
cd dsa4265-project
source .venv/bin/activate
cd backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Terminal 2:

```bash
cd dsa4265-project/frontend
npm run dev
```

Then open:

```text
http://localhost:3000
```

To confirm the backend is alive, open:

```text
http://localhost:8000/api/v1/health
```

To confirm model artifacts are loadable, open:

```text
http://localhost:8000/api/v1/health/models
```

## Fallback and Demo Behavior

- Default-risk scoring uses the local artifact at `backend/app/models/credit_risk_lgbm.joblib`.
- Anomaly scoring uses local artifacts under `backend/app/models/ae_agent/`.
- If either model artifact is missing or cannot be loaded, `/api/v1/process` returns a `503` with diagnostic details.
- If `OPENROUTER_API_KEY` is missing, the optional AI decision path is skipped and the backend uses a deterministic fallback AI decision derived from rule output.
- If `OPENROUTER_API_KEY` is missing or an explanation LLM call fails, `/api/v1/explain` returns an "explanation unavailable" response with key metrics and a limitation message instead of failing the whole app.
- If chatbot LLM generation fails, `/api/v1/chat` falls back to local policy retrieval output and returns citations when available.
- The chatbot memory is in-process only. It is suitable for local demos, not persistent production sessions.

## Limitations / External Dependencies

- OpenRouter-backed LLM features require network access and a valid `OPENROUTER_API_KEY`.
- The policy retrieval module contains optional heavier paths for `sentence-transformers`, `rank_bm25`, and `transformers`, but the chatbot's fast runtime path is configured to use local fallback retrieval and does not require those packages.
- Model artifacts are bundled in the repository. If they are removed, moved, or replaced, update `CREDIT_MODEL_PATH` and `ANOMALY_MODEL_DIR`.
- CORS is currently permissive in `backend/app/main.py` for local development.
- Docker Compose is intended for local development, not hardened deployment.

## Troubleshooting

### `ModuleNotFoundError: No module named 'app'`

Run Uvicorn from inside `backend/`:

```bash
cd backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Frontend says the backend request failed

Check that the backend is running at `http://localhost:8000` and that this health URL works:

```text
http://localhost:8000/api/v1/health
```

If you run the backend on a different port, set `NEXT_PUBLIC_API_BASE_URL` in `frontend/.env.local`.

### Model readiness reports missing artifacts

Check:

```text
backend/app/models/credit_risk_lgbm.joblib
backend/app/models/ae_agent/preprocessor.pkl
backend/app/models/ae_agent/metadata.pkl
backend/app/models/ae_agent/autoencoder_model.pt
```

If you use custom artifact locations, export `CREDIT_MODEL_PATH` and `ANOMALY_MODEL_DIR` before starting the backend.

The first readiness check may also take time because it imports model libraries and loads the anomaly artifacts. Use Python 3.11 as recommended if readiness is unusually slow in another interpreter.

### Explanations or chat say the LLM is unavailable

Set `OPENROUTER_API_KEY` and restart the backend:

```bash
export OPENROUTER_API_KEY="<your-openrouter-api-key>"
```

The rest of the local scoring workflow can still run without this key.

### `pip install` fails for model packages

Use Python 3.11 where possible. The backend Dockerfile also uses Python 3.11, which is the safest target for dependency compatibility.

### `npm install` fails

Use Node.js 20. For a clean install:

```bash
cd frontend
rm -rf node_modules
npm ci
```

### Docker Compose frontend cannot reach backend

Confirm both containers are running:

```bash
docker compose ps
```

Then check the backend directly from your browser:

```text
http://localhost:8000/api/v1/health
```
