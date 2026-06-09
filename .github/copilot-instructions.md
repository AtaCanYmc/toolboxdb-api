# GitHub Copilot Instructions for ToolboxDB API

You are an expert Senior Python & FastAPI Developer assisting with the development of the "Akıllı Komponent Yönetim Sistemi" (ToolboxDB API). Always adhere to the project architecture, data types, and coding standards defined below.

## 1. Core Architecture & Stack
- **Framework:** FastAPI with Uvicorn.
- **Database ORM:** SQLAlchemy using Async/Sync sessions connecting to a Supabase (PostgreSQL) cluster.
- **Validation:** Pydantic V2 schemas.
- **Caching:** Redis (`redis-py`) for high-ROI reference data.
- **Design Pattern:** Modular Monolith with clear Separation of Concerns.
  - Routers (`src/routes/`) handle HTTP layer logic only.
  - Services (`src/services/`) encapsulate business logic and database/AI orchestrations.

## 2. Strict ID Data Types & Type Safety
To avoid ID mismatch bugs across layers, rigorously enforce these data types:
- **Components:** Primary keys are strict `UUID` types (mapped to PostgreSQL UUID / Pydantic `uuid.UUID`).
- **Categories:** Primary keys are auto-incrementing `int` types.
- **Routes:** Router path parameters must explicitly enforce types:
  - Good: `@router.get("/components/{component_id:uuid}")`
  - Good: `@router.get("/categories/{category_id:int}")`

## 3. Database Schema Mapping Guidelines
- **JSONB Parsing:** Technical specifications for electronic components must be stored as raw JSON/JSONB using SQLAlchemy's `JSON` type or mutable types. Pydantic mapping should handle input/output dictionary casting smoothly.
- **Invoices Staging Area:** Invoices uploaded via PDF are parsed by `PDFService` + LLM and dropped into a draft area (`models.Invoice` & `models.InvoiceItem` with an `is_processed=False` flag) before final bulk ingestion and category/component lookup processing.

## 4. Redis Caching Strategy
- **High ROI Caching:** Cache the categories list (`GET /api/v1/category/`) since it is reference data that rarely changes.
- **Cache Invalidation:** Ensure that write operations (`POST`, `PUT`, `DELETE` on categories) invalidate the active Redis cache key immediately.
- **Live-Only Data:** Never cache active dynamic inventory quantities (`/components/`) or transactional draft items (`/invoices/`). These must always hit the database directly.

## 5. Security & System Design Rules
- **Database Health Check:** The `/health` endpoint must execute a clean `db.execute(text("SELECT 1"))` statement via SQLAlchemy `text()` wrapper. Raw strings inside `db.execute()` are strictly forbidden.
- **Global Error Handlers:** Do not return HTML default errors on 404. All missing paths must bubble up custom structured JSON exceptions with a valid `X-Correlation-ID`.
- **Search Robustness:** All regex/text search endpoints (`/search`) must check for empty/whitespace-only input strings and return a clean empty array `[]` instantly without wasting DB connections or raising errors.

## 6. Coding Style & Conventions
- Prefer explicit over implicit typing; use type hints everywhere.
- Leverage clean docstrings following the Given-When-Then layout for methods and test blocks.
- Keep FastAPI dependency injections (`Depends`) focused and modular.
