"""FastAPI dependencies: optional API key, tenant isolation."""
from __future__ import annotations

from fastapi import Header, HTTPException

from app.config import get_settings
from app.tenant_paths import normalize_tenant_id


async def verify_api_key_if_set(
    x_api_key: str | None = Header(None, alias="X-API-Key"),
    authorization: str | None = Header(None),
) -> None:
    """When API_KEY is set in the environment, require X-API-Key or Authorization: Bearer."""
    settings = get_settings()
    expected = (settings.api_key or "").strip()
    if not expected:
        return
    token = (x_api_key or "").strip()
    if authorization and authorization.lower().startswith("bearer "):
        token = authorization[7:].strip()
    if token != expected:
        raise HTTPException(status_code=401, detail="Invalid or missing API key")


def get_tenant_id(x_tenant_id: str | None = Header(None, alias="X-Tenant-ID")) -> str:
    """Workspace / tenant scope for data isolation (header defaults to `default`)."""
    try:
        return normalize_tenant_id(x_tenant_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
