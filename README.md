# FORGE

Week 1 delivers a production-ready PDF upload and editor flow with deterministic extraction foundations.

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

## Deploy to Railway

1. Create a new Railway project and connect this GitHub repository.
2. Create **two services** from the same repo.

### Service 1: API

- **Root Directory**: `apps/api`
- **Build**: Railway will detect the `Dockerfile` automatically.
- **Start Command**: Use the Dockerfile entrypoint (do not override).
- **Environment variables**:
  - `FORGE_STORAGE_LOCAL_DIR=.data`
  - `WEB_ORIGIN=https://<your-web-service-url>`
  - `LOG_LEVEL=INFO`
  - `OPENAI_API_KEY=...`
  - `OPENAI_MODEL=gpt-5.2` (optional override)

### Service 2: Web

- **Root Directory**: `apps/web`
- **Build**: Railway will detect the `Dockerfile` automatically.
- **Start Command**: Use the Dockerfile entrypoint (do not override).
- **Environment variables**:
  - `NEXT_PUBLIC_API_BASE_URL=https://<your-api-service-url>`

### Notes

- Each service uses its own Dockerfile, and Railway injects the `PORT` environment variable automatically.
- CORS is controlled by `WEB_ORIGIN` on the API; it must match the deployed Web URL.
- The OpenAI key is required only for AI planning endpoints and stays server-side in the API service.
