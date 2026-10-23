"""FastAPI app: POST /search and POST /ask, bound to 127.0.0.1 only.

    uvicorn api.main:app --host 127.0.0.1 --port 8000      (or: python -m api.main)

Spend control: every paid call (query embedding, answer, verification) goes through the file-backed ledger in api/ledger.py, which reserves
the full worst-case charge before the call and settles to real usage afterwards; an over-budget request returns 429 and makes no paid call.
"""
import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Literal

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field, field_validator
from starlette.middleware.trustedhost import TrustedHostMiddleware

from api.ledger import Ledger
from api.service import ApiError, Services, do_ask, do_search

MAX_QUERY_CHARS = 500
MAX_BODY_BYTES = 4096
LOCAL_HOSTS = ["127.0.0.1", "localhost"]


def _clean_query(v: str) -> str:
    v = v.strip()
    if not v:
        raise ValueError("must not be empty")
    if any(ord(c) < 32 and c not in "\t\n" for c in v):
        raise ValueError("contains control characters")
    return v


class SearchRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    query: str = Field(max_length=MAX_QUERY_CHARS)
    mode: Literal["bm25", "dense", "hybrid"]
    chunker: Literal["fixed", "heading"] = "heading"
    k: int = Field(10, ge=1, le=50)

    check_query = field_validator("query")(_clean_query)


class AskRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    query: str = Field(max_length=MAX_QUERY_CHARS)

    check_query = field_validator("query")(_clean_query)


def build_services_from_env() -> Services:
    """Real services. Keys are read from the environment by the provider SDKs only; this module never touches their values."""
    from dotenv import load_dotenv
    from elasticsearch import Elasticsearch

    from ingest.embed_cache import SpendGuard  # noqa: F401  (imported for symmetry with eval code)
    from rag.query_cache import QueryCache, serving_path
    from rag.retrieve import QueryEmbedder

    load_dotenv()
    embed_model = os.environ.get("EMBED_MODEL", "text-embedding-3-small")
    ing = f"data/embed_cache/{embed_model}.jsonl"
    serving = QueryCache(serving_path(ing))

    def openai_client():
        from openai import OpenAI
        return OpenAI(max_retries=0)

    def anthropic_client():
        import anthropic
        return anthropic.Anthropic()

    return Services(
        es=Elasticsearch(os.environ.get("ES_URL", "http://127.0.0.1:9200")), index=os.environ.get("ES_INDEX", "rag-docs"),
        ledger=Ledger(limit_usd=float(os.environ.get("MAX_SPEND_USD", "5"))),
        make_embedder=lambda guard: QueryEmbedder(ing, embed_model, openai_client, guard, serving_cache=serving, legacy_fallback=False),
        client_factory=anthropic_client, answer_model=os.environ["ANSWER_MODEL"], verifier_model=os.environ["VERIFIER_MODEL"], log_dir=Path("data/api"))


def create_app(svc: Services | None = None, allowed_hosts: list[str] | None = None) -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        if not hasattr(app.state, "svc"):
            app.state.svc = build_services_from_env()
        app.state.svc.ledger.recover_stale()  # reservations left open by a crash count as spent
        yield

    app = FastAPI(title="rag-hybrid", docs_url=None, redoc_url=None, openapi_url=None, lifespan=lifespan)
    if svc is not None:
        app.state.svc = svc
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=allowed_hosts or LOCAL_HOSTS)

    @app.middleware("http")
    async def limit_body(request: Request, call_next):
        if request.method in ("POST", "PUT", "PATCH"):
            cl = request.headers.get("content-length")
            if cl is None:
                return JSONResponse({"error": {"code": "length_required", "message": "Content-Length is required."}}, status_code=411)
            if not cl.isdigit() or int(cl) > MAX_BODY_BYTES:
                return JSONResponse({"error": {"code": "payload_too_large", "message": f"Request body must be at most {MAX_BODY_BYTES} bytes."}}, status_code=413)
        return await call_next(request)

    @app.exception_handler(ApiError)
    async def api_error(request: Request, e: ApiError):
        return JSONResponse({"error": {"code": e.code, "message": e.message, **e.extra}}, status_code=e.status)

    @app.exception_handler(RequestValidationError)
    async def invalid(request: Request, e: RequestValidationError):
        fields = [{"field": ".".join(str(p) for p in err["loc"] if p != "body"), "problem": err["msg"]} for err in e.errors()]  # never echoes the input
        return JSONResponse({"error": {"code": "invalid_request", "message": "The request is not valid.", "fields": fields}}, status_code=422)

    @app.exception_handler(Exception)
    async def unexpected(request: Request, e: Exception):
        return JSONResponse({"error": {"code": "internal_error", "message": "Internal error."}}, status_code=500)

    @app.get("/health")
    def health(request: Request):
        s = request.app.state.svc.ledger.status()
        return {"status": "ok", "spend": {"limit_usd": s["limit_usd"], "remaining_usd": s["remaining_usd"]}}

    @app.post("/search")
    def search(body: SearchRequest, request: Request):
        return do_search(request.app.state.svc, body.query, body.mode, body.chunker, body.k)

    @app.post("/ask")
    def ask(body: AskRequest, request: Request):
        return do_ask(request.app.state.svc, body.query)

    return app


app = create_app()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api.main:app", host="127.0.0.1", port=int(os.environ.get("PORT", "8000")))
