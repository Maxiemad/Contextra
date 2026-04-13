"""FastAPI entrypoint: Multimodal RAG API."""
from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.deps import verify_api_key_if_set
from app.routers import chunks, jobs, query, sources, upload

settings = get_settings()
app = FastAPI(
    title="Multimodal RAG",
    description="NotebookLM-style retrieval-augmented generation with citations. "
    "Use X-Tenant-ID for workspace isolation; optional API_KEY enforces X-API-Key or Bearer.",
    version="1.0.0",
)

origins = [o.strip() for o in settings.cors_origins.split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins or ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

_protected = [Depends(verify_api_key_if_set)]

app.include_router(upload.router, prefix="", dependencies=_protected)
app.include_router(query.router, prefix="", dependencies=_protected)
app.include_router(sources.router, prefix="", dependencies=_protected)
app.include_router(chunks.router, prefix="", dependencies=_protected)
app.include_router(jobs.router, prefix="", dependencies=_protected)


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}
