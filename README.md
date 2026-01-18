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

## Deploy to Railway (Monorepo, two services)

1. Create a new Railway project and connect this GitHub repository.
2. Create **two services** from the same repo.

### Service 1: API

- **Root Directory**: `apps/api`
- **Build**: Railway detects the `Dockerfile`.
- **Start Command**: Use the Dockerfile entrypoint (do not override).

**Required env vars**

| Variable | Example | Notes |
| --- | --- | --- |
| `WEB_ORIGIN` | `https://<your-web-service-url>` | Comma-separated allowed origins. Required in production. |
| `FORGE_STORAGE_DRIVER` | `s3` or `local` | Storage backend selection. |
| `FORGE_STORAGE_LOCAL_DIR` | `.data` | Used when `FORGE_STORAGE_DRIVER=local`. |
| `FORGE_MAX_UPLOAD_MB` | `25` | Upload limit in MB. |
| `FORGE_EXPORT_MASK_MODE` | `AUTO_BG` | Default export mask mode. |

**S3-only env vars**

| Variable | Example | Notes |
| --- | --- | --- |
| `FORGE_S3_BUCKET` | `forge-prod` | Required for S3. |
| `FORGE_S3_REGION` | `us-east-1` | Optional. |
| `FORGE_S3_ACCESS_KEY` | `...` | Required for S3. |
| `FORGE_S3_SECRET_KEY` | `...` | Required for S3. |
| `FORGE_S3_ENDPOINT` | `https://<r2-endpoint>` | Optional for R2/MinIO. |
| `FORGE_S3_PREFIX` | `forge/` | Optional prefix. |

**Optional env vars**

| Variable | Example | Notes |
| --- | --- | --- |
| `OPENAI_API_KEY` | `sk-...` | Only for AI patch planning (server-side only). |
| `OPENAI_MODEL` | `gpt-5.2` | Optional override. |
| `FORGE_PATCH_STORE_DRIVER` | `s3` | Defaults to storage driver. |
| `FORGE_EXPORT_MASK_SOLID_COLOR` | `255,255,255` | RGB for solid mask fill. |
| `FORGE_BUILD_VERSION` | `2024.10.01` | Shown in `/health`. |
| `LOG_LEVEL` | `INFO` | Logging verbosity. |
| `FORGE_ENV` | `production` | Controls CORS defaults. |

### Service 2: Web

- **Root Directory**: `apps/web`
- **Build**: Railway detects the `Dockerfile`.
- **Start Command**: Use the Dockerfile entrypoint (do not override).

**Env vars**

| Variable | Example | Notes |
| --- | --- | --- |
| `NEXT_PUBLIC_API_BASE_URL` | `https://<your-api-service-url>` | API base URL for the browser. |

### Optional non-Docker Railway commands

If you choose not to use the Dockerfiles:

**API**

- Build: `pip install -r requirements.txt`
- Start: `uvicorn forge_api.main:app --host 0.0.0.0 --port $PORT`

**Web**

- Build: `pnpm install && pnpm build`
- Start: `pnpm start` (or `next start -p $PORT`)

### Notes

- Each service uses its own Dockerfile, and Railway injects the `PORT` environment variable automatically.
- CORS is controlled by `WEB_ORIGIN` on the API; it must match the deployed Web URL.
- The OpenAI key is required only for AI planning endpoints and stays server-side in the API service.
- The `pnpm check` script includes a no-binaries guard to keep the repo free of PDFs/images/fonts.
