# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Receipt Scanner for Firefly III — a FastAPI web app that scans receipts using Google Gemini AI and creates transactions in Firefly III. Mobile-friendly with PWA support and camera capture.

## Commands

```bash
docker-compose up -d             # build and run on port 8000
docker-compose up -d --build     # rebuild after code changes
uv sync --frozen                 # install deps locally (for IDE support)
```

No test suite or linter is currently configured.

## Architecture

Three-tier FastAPI application with Jinja2 server-side rendering:

```
User → FastAPI (app.py) → Google Gemini AI (receipt_processing.py)
                        → Firefly III API (firefly.py)
                        → Image preprocessing (image_utils.py)
```

### Request Flow
1. `GET /` — upload form, fetches asset accounts from Firefly III
2. `POST /extract` — receives image + source account, processes image (resize/compress via `image_utils.py`), sends to Gemini with categories/budgets from Firefly III, returns review form
3. `POST /create-transaction` — validates via `ReceiptModel`, creates withdrawal in Firefly III with `#automated` tag, 3 retries with exponential backoff

### Key Modules
- **app.py** — FastAPI routes, middleware (ProxyHeaders, TrustedHost), static file mounting, startup validation of Firefly III connection
- **receipt_processing.py** — Gemini AI integration (model configurable via `GEMINI_MODEL`, defaults to `gemini-2.5-flash`), dynamic prompt construction with Firefly categories/budgets, structured JSON response via `ReceiptModel` schema
- **firefly.py** — Firefly III REST API client (accounts, categories, budgets, transaction creation), 30s timeout, comprehensive HTTP error handling
- **image_utils.py** — PIL image processing: RGB conversion, resize to max 768×768 with aspect ratio preservation
- **models.py** — `ReceiptModel` Pydantic model (date, amount, store_name, description, category, budget)
- **templates/** — Jinja2 templates: `base.html` (layout + PWA meta), `upload.html`, `review.html`, `error.html`

### Configuration
Environment variables loaded via `dotenv` (see `.env.example`):
- `FIREFLY_III_URL` — Firefly III instance base URL
- `FIREFLY_III_TOKEN` — Firefly III personal access token
- `GOOGLE_AI_API_KEY` — Google Gemini API key
- `GEMINI_MODEL` — Gemini model name (e.g. `gemini-2.5-flash`)

### Tech Stack
Python 3.13, FastAPI, Uvicorn, Jinja2, Pydantic, Pillow, google-genai, uv (package manager), Docker
