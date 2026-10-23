# API image: minimal, non-root, fully pinned. Contains code only: no .env, no keys, no data/, no corpus, no eval results.
FROM python:3.12-slim@sha256:a0f57064cbdcd6285fa45f51237ab0b35ea8ebaed06a1f5973e89e19dfb86704

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1 PIP_DISABLE_PIP_VERSION_CHECK=1 \
    TIKTOKEN_CACHE_DIR=/opt/tiktoken

RUN useradd --system --uid 10001 --no-create-home --shell /usr/sbin/nologin app

WORKDIR /app
COPY requirements-api.txt .
RUN pip install -r requirements-api.txt

# tiktoken downloads its encoding on first use; bake it in at build time so the running container needs no other outbound host
RUN python -c "import tiktoken; tiktoken.get_encoding('cl100k_base')" && chmod -R a+rX /opt/tiktoken

COPY api ./api
COPY rag ./rag
COPY ingest/__init__.py ingest/embed_cache.py ./ingest/

# the ledger, the request logs and the serving query cache live here; compose mounts a volume over it so they survive recreation
RUN mkdir -p /app/data && chown -R app:app /app/data
USER app

EXPOSE 8000
# 0.0.0.0 is the container's own interface; the host publishes the port on 127.0.0.1 only (docker-compose.yml)
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
