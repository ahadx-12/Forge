FROM python:3.11-slim

WORKDIR /app

# Copy requirements from the build context (apps/api)
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
RUN python -m playwright install --with-deps chromium

# Copy the rest of the API source
COPY . .

ENV PYTHONPATH=src

CMD ["sh", "-c", "uvicorn forge_api.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
