# FORGE

Week 1 delivers a production-ready PDF upload + editor flow with deterministic extraction foundations.

## Local development

### API

```bash
cd apps/api
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn forge_api.main:app --host 0.0.0.0 --port 8000
```

### Web

```bash
cd apps/web
pnpm install
pnpm dev
```

Then open `http://localhost:3000` and upload a PDF on the dashboard.

## Running checks

```bash
pnpm check
```

## Railway deployment

Create two services:

### API service
- Root directory: `apps/api`
- Start command: `Dockerfile`
- Environment variables:
  - `FORGE_STORAGE_LOCAL_DIR=/data` (or a mounted volume)
  - `WEB_ORIGIN=https://your-web-domain`

### Web service
- Root directory: `apps/web`
- Start command: `Dockerfile`
- Environment variables:
  - `NEXT_PUBLIC_API_BASE_URL=https://your-api-domain`

## Environment variables

See `.env.example` for local defaults.
