"""FastAPI entrypoint: Multimodal RAG API."""
from __future__ import annotations

import logging
import os

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.deps import verify_api_key_if_set
from app.routers import chunks, jobs, query, sources, upload

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s %(levelname)s %(name)s - %(message)s",
)
logger = logging.getLogger("contextra")

settings = get_settings()


def _build_allowed_origins() -> list[str]:
    """Merge FRONTEND_URL + CORS_ORIGINS into a deduped list of explicit origins."""
    raw: list[str] = []
    if settings.frontend_url:
        raw.append(settings.frontend_url)
    if settings.cors_origins:
        raw.extend(settings.cors_origins.split(","))
    cleaned = []
    for o in raw:
        o = o.strip().rstrip("/")
        if o and o not in cleaned:
            cleaned.append(o)
    return cleaned


allowed_origins = _build_allowed_origins()
# If the operator explicitly wrote "*" anywhere, honor it (but then we must NOT
# advertise credentials, per CORS spec).
wildcard = "*" in allowed_origins
allow_credentials = not wildcard

app = FastAPI(
    title="Contextra — Multimodal RAG",
    description=(
        "NotebookLM-style retrieval-augmented generation with citations. "
        "Use X-Tenant-ID for workspace isolation; optional API_KEY enforces X-API-Key or Bearer."
    ),
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if wildcard else allowed_origins,
    allow_credentials=allow_credentials,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
    max_age=600,
)

_protected = [Depends(verify_api_key_if_set)]

app.include_router(upload.router, prefix="", dependencies=_protected)
app.include_router(query.router, prefix="", dependencies=_protected)
app.include_router(sources.router, prefix="", dependencies=_protected)
app.include_router(chunks.router, prefix="", dependencies=_protected)
app.include_router(jobs.router, prefix="", dependencies=_protected)


@app.on_event("startup")
async def _startup_banner() -> None:
    logger.info("=" * 60)
    logger.info("Contextra backend starting")
    logger.info("LLM backend:     %s", settings.llm_backend)
    logger.info("Ollama URL:      %s", settings.ollama_base_url)
    logger.info("Groq configured: %s", bool((os.getenv("GROQ_API_KEY") or settings.groq_api_key).strip()))
    logger.info("Embeddings:      SentenceTransformers/%s", settings.st_model_name)
    logger.info("Data dir:        %s", settings.data_dir)
    logger.info("CORS allow:      %s (credentials=%s)", allowed_origins or ["*"], allow_credentials)
    logger.info("=" * 60)


@app.get("/")
async def root() -> dict:
    """Render's port-detector pings `/` — give it a real response."""
    return {
        "service": "contextra",
        "status": "ok",
        "docs": "/docs",
        "health": "/health",
    }


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}