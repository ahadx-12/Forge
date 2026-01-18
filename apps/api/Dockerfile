FROM python:3.11-slim

WORKDIR /app

# Copy requirements first for caching
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the API app (including src/)
COPY . .

ENV PYTHONPATH=src

CMD ["sh", "-c", "uvicorn forge_api.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
