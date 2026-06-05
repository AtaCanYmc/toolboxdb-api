# Intelligent Component Management System (ToolboxDB API)

![Python 3.11](https://img.shields.io/badge/python-3.11-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-Framework-brightgreen)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-Database-blue)
![Redis](https://img.shields.io/badge/Redis-Cache-orange)
![GitHub Actions CI](https://img.shields.io/badge/GitHub%20Actions-CI-white)

## Project Overview
The **Intelligent Component Management System (ToolboxDB API)** is built for makers and IoT developers to track component lifecycles, automatically ingest invoice and batch data via AI/LLM-powered PDF parsing, and optimize query performance using Redis caching. Parsed invoices are stored in a staging area for verification before being mapped to inventory, ensuring safe and auditable ingestion.

## Core Features
The table below summarizes the system's primary capabilities:

| Feature | Description |
|---|---|
| **Automated PDF Invoice Parsing (LLM)** | LLM-driven pipeline that extracts structured outputs (line items, quantities, suppliers, dates) from PDF invoices. |
| **Staging / Draft Area** | Parsed invoices are saved as drafts (`is_processed = False`) in `Invoice`/`InvoiceItem` models for manual or automated review before final ingestion. |
| **Modular Monolith Architecture & ID Type Safety** | `src/routes` handles HTTP concerns only; business logic lives in `src/services`. Strict typing: **Components** use `UUID`, **Categories** use `int`, and route path parameters enforce these types. |
| **High-ROI Redis Caching** | Reference data (e.g., category lists) are cached in Redis. Write operations (POST/PUT/DELETE) immediately invalidate relevant cache keys. Dynamic inventory counts are never cached. |
| **Production-ready Operational Features** | Correlation ID propagation, a `/health` endpoint that uses SQLAlchemy `text("SELECT 1")` for DB health checks, and Dockerized CI pipelines. |

Key notes:
- End-to-end invoice → draft → review → inventory mapping workflow.
- Router-level type safety: `component_id:uuid`, `category_id:int`.
- Strict cache invalidation policy and `X-Correlation-ID` support for tracing.

## Tech Stack
- Framework & Server:
  - FastAPI (ASGI)
  - Uvicorn (development/production runner)
- Database & ORM:
  - Supabase (PostgreSQL)
  - SQLAlchemy (async/sync)
- Cache:
  - Redis (`redis-py`)
- PDF & LLM:
  - pypdf (PDF parsing)
  - OpenAI / Ollama (LLM provider adapters)
- Testing & QA:
  - Pytest
  - Black / Flake8
- Other:
  - Pydantic v2

## Project Structure (Highlights)
Focus areas and directory layout:

```
toolboxdb-api/
├─ main.py
├─ requirements.txt
├─ .github/
│  └─ workflows/
│     └─ ci.yml        # Linting + Test + Redis service container
├─ src/
│  ├─ __init__.py
│  ├─ cache.py
│  ├─ db/
│  │  └─ connector.py
│  ├─ llm/
│  │  └─ ...          # LLM provider adapters (openai, ollama, groq)
│  ├─ middleware/
│  │  └─ middleware.py # Correlation ID, error handling, request validation
│  ├─ pdf/
│  │  └─ pdf_service.py # PDF -> LLM parsing pipeline
│  ├─ routes/
│  │  ├─ category_routes.py
│  │  ├─ component_routes.py
│  │  └─ core_routes.py
│  ├─ services/
│  │  └─ ...          # Business logic, data mapping, transaction management
│  ├─ models.py
│  └─ schemas.py
├─ tests/
│  ├─ test_component_routes.py
│  └─ test_pdf_service.py
└─ docks/
   └─ REDIS_SETUP.md
```

## Installation & Local Setup (zsh)
These steps assume macOS with zsh:

1. Clone the repository:
```bash
git clone <REPO_URL> toolboxdb-api
cd toolboxdb-api
```

2. Create and activate a virtual environment (`.venv`):
```bash
python3.11 -m venv .venv
source .venv/bin/activate
```

3. Install dependencies:
```bash
pip install --upgrade pip
pip install -r requirements.txt
```

4. Start a local Redis container for development:
```bash
docker run -d --name toolboxdb-redis -p 6379:6379 redis:7
```

5. Environment variables (example):
```bash
export DATABASE_URL=postgresql://user:pass@localhost:5432/toolboxdb
export REDIS_URL=redis://localhost:6379/0
export OPENAI_API_KEY=sk-...
```

6. Start the development server with Uvicorn:
```bash
uvicorn main:app --reload
```

The application typically runs at `http://127.0.0.1:8000`. Swagger UI: `http://127.0.0.1:8000/docs`

## Health Checks & Security Notes
- The `/health` endpoint should perform a safe SQLAlchemy check using: `db.execute(text("SELECT 1"))`.
- Missing routes and errors return structured JSON error responses (no HTML error pages).
- Search endpoints validate empty/whitespace-only input and return `[]` immediately to avoid unnecessary DB connections.

## CI/CD (Brief)
- The repository includes a GitHub Actions workflow (`.github/workflows/ci.yml`) that:
  - Runs formatting and lint checks (Black, Flake8)
  - Runs tests (Pytest)
  - Uses a Redis service container during tests so test suites requiring Redis can run in CI
  - Can be extended with Docker image builds and integration steps

## Operational Recommendations
- **Cache Invalidation:** Ensure category write operations immediately invalidate Redis keys.
- **Invoice Staging:** Persist LLM-parsed invoice outputs as `Invoice` objects with `is_processed=False` for review; mark `is_processed=True` after validation and then map to inventory.
- **Type Safety:** Enforce route path parameter types explicitly in routers:
  - `@router.get("/components/{component_id:uuid}")`
  - `@router.get("/categories/{category_id:int}")`

---
