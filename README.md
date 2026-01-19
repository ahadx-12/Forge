# FORGE

FORGE is a precision PDF editor built around deterministic decoding, stable IDs, and JSON patch operations.

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

## Smoke test (optional)

Run against a live API container/service:

```bash
cd apps/api
python scripts/smoke.py
```

The script generates a PDF at runtime, uploads it, hit-tests, commits a patch, composites IR, and exports a PDF.

## Deployment on Railway (Monorepo, two services)

Create a new Railway project, connect this repo, and create **two services** (Web + API) from the same repository.

### Recommended Railway service configuration

**API service (FastAPI)**

- **Service Root Dir**: `apps/api`
- **Build Command**: `python -m pip install -r requirements.txt`
- **Start Command**: `sh -c "uvicorn forge_api.main:app --host 0.0.0.0 --port ${PORT:-8000}"`

**Web service (Next.js)**

- **Service Root Dir**: `apps/web`
- **Build Command**: `pnpm install --frozen-lockfile && pnpm --filter ./apps/web build`
- **Start Command**: `pnpm --filter ./apps/web start -- -p ${PORT:-3000}`

If Railway builds from the repo root, the root `package.json` includes `build` and `start` scripts that target the Web app.

### API environment variables

**Required**

| Variable | Example | Notes |
| --- | --- | --- |
| `FORGE_STORAGE_DRIVER` | `s3` or `local` | Storage backend selection. |
| `WEB_ORIGIN` | `https://<your-web-service-url>` | Comma-separated allowed origins for CORS. Required in production. |
| `FORGE_MAX_UPLOAD_MB` | `25` | Upload limit in MB. |
| `FORGE_EXPORT_MASK_MODE` | `AUTO_BG` | Default export mask mode. |

**S3/R2 storage**

| Variable | Example | Notes |
| --- | --- | --- |
| `FORGE_S3_BUCKET` | `forge` | Required when `FORGE_STORAGE_DRIVER=s3`. |
| `FORGE_S3_ENDPOINT` | `https://<accountid>.r2.cloudflarestorage.com` | Cloudflare R2 endpoint format. |
| `FORGE_S3_ACCESS_KEY` | `***` | Required for S3. |
| `FORGE_S3_SECRET_KEY` | `***` | Required for S3. |
| `FORGE_S3_REGION` | `auto` | Use `auto` for R2 or leave blank if your runtime ignores it. |
| `FORGE_S3_PREFIX` | `optional/prefix` | Optional key prefix (can be empty). |

**Local storage**

| Variable | Example | Notes |
| --- | --- | --- |
| `FORGE_STORAGE_LOCAL_DIR` | `.data` | Used when `FORGE_STORAGE_DRIVER=local`. |

**Optional**

| Variable | Example | Notes |
| --- | --- | --- |
| `OPENAI_API_KEY` | `***` | Only for AI patch planning (server-side only). |
| `OPENAI_MODEL` | `gpt-5.2` | Optional override. |
| `FORGE_PATCH_STORE_DRIVER` | `s3` | Defaults to storage driver. |
| `FORGE_EXPORT_MASK_SOLID_COLOR` | `255,255,255` | RGB for solid mask fill. |
| `FORGE_BUILD_VERSION` | `2024.10.01` | Shown in `/health`. |
| `LOG_LEVEL` | `INFO` | Logging verbosity. |
| `FORGE_ENV` | `production` | When set to `production`, CORS is disabled unless `WEB_ORIGIN` is configured. |

### AI patch planning configuration + error codes

AI patch planning runs **only** in `apps/api`. In production you must set:

- `OPENAI_API_KEY` (required)
- `OPENAI_MODEL` (optional override, defaults to `gpt-5.2`)

If AI is misconfigured or upstream errors occur, the API responds with structured JSON:

| HTTP | `error` code | Meaning |
| --- | --- | --- |
| 503 | `ai_not_configured` | Missing/invalid `OPENAI_API_KEY`. |
| 400 | `invalid_model` | Invalid `OPENAI_MODEL` (check model name). |
| 502 | `ai_rate_limited` / `ai_timeout` / `ai_connection_error` / `ai_upstream_error` | OpenAI request failed (retryable). |
| 400 | `missing_selection` | AI planning request missing selection/candidates. |
| 409 | `patch_target_not_found` | Patch commit target no longer exists. |

### Web environment variables

| Variable | Example | Notes |
| --- | --- | --- |
| `NEXT_PUBLIC_API_BASE_URL` | `https://<your-api-service-url>` | API base URL used by the browser (no trailing slash). |

### CORS guidance

- `WEB_ORIGIN` accepts a comma-separated list of allowed origins (e.g. `https://forge.app,https://staging.forge.app`).
- In production (`FORGE_ENV=production`), leave `WEB_ORIGIN` empty only if you intend to disable browser access.

### Verification after deploy

1. Open the Web service URL and upload a PDF on the dashboard.
2. Confirm the app redirects to `/editor/{docId}`.
3. Confirm the editor loads the document metadata and decoded pages.
4. Open the API `/health` endpoint to verify storage driver and environment settings.
