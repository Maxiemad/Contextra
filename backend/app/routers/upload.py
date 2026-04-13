"""POST /upload, POST /upload/async, /upload/text/async, /upload/url/async"""
import hashlib
import re
from pathlib import Path

import httpx
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile

from app.config import get_settings
from app.deps import get_tenant_id
from app.ingestion import guess_source_type
from app.models.schemas import (
    AsyncUploadAcceptedItem,
    SourceType,
    TextPasteRequest,
    UploadResponse,
    UrlFetchRequest,
)
from app.services.ingestion_jobs import get_job_store
from app.services.ingestion_worker import spawn_ingestion_thread
from app.services.upload_service import process_upload
from app.services.url_fetch import fetch_url_content, is_safe_http_url
from app.tenant_paths import tenant_upload_dir

router = APIRouter(prefix="/upload", tags=["upload"])


def _safe_txt_filename(title: str | None, fallback: str) -> str:
    base = (title or fallback).strip() or fallback
    base = "".join(c if c.isalnum() or c in "._- " else "_" for c in base)
    base = re.sub(r"_+", "_", base).strip("._ ")[:120] or fallback
    if not base.lower().endswith(".txt"):
        base = f"{base}.txt"
    return base


@router.post("", response_model=list[UploadResponse])
async def upload_files(
    files: list[UploadFile] = File(...),
    tenant_id: str = Depends(get_tenant_id),
) -> list[UploadResponse]:
    if not files:
        raise HTTPException(400, "No files uploaded.")
    settings = get_settings()
    out: list[UploadResponse] = []
    upload_root = tenant_upload_dir(tenant_id)
    for uf in files:
        if not uf.filename:
            continue
        data = await uf.read()
        max_b = settings.max_upload_mb * 1024 * 1024
        if len(data) > max_b:
            raise HTTPException(413, f"File exceeds {settings.max_upload_mb} MB limit.")
        st = guess_source_type(uf.filename, uf.content_type)
        safe_name = Path(uf.filename).name
        stem = Path(safe_name).stem
        suffix = Path(safe_name).suffix
        tag = hashlib.sha256(data).hexdigest()[:16]
        dest = upload_root / f"{stem}_{tag}{suffix}"
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(data)
        out.append(process_upload(tenant_id, dest, safe_name, st))
    if not out:
        raise HTTPException(400, "No valid files.")
    return out


@router.post("/async", response_model=list[AsyncUploadAcceptedItem], status_code=202)
async def upload_files_async(
    files: list[UploadFile] = File(...),
    tenant_id: str = Depends(get_tenant_id),
) -> list[AsyncUploadAcceptedItem]:
    """
    Accept files, return job ids immediately. Processing runs in a background thread
    (large PDFs / video transcription won't block the HTTP request).
    Poll GET /jobs/{job_id} until status is completed or failed.
    """
    if not files:
        raise HTTPException(400, "No files uploaded.")
    settings = get_settings()
    store = get_job_store(tenant_id)
    accepted: list[AsyncUploadAcceptedItem] = []
    upload_root = tenant_upload_dir(tenant_id)

    for uf in files:
        if not uf.filename:
            continue
        data = await uf.read()
        max_b = settings.max_upload_mb * 1024 * 1024
        if len(data) > max_b:
            raise HTTPException(413, f"File exceeds {settings.max_upload_mb} MB limit.")
        st = guess_source_type(uf.filename, uf.content_type)
        safe_name = Path(uf.filename).name
        stem = Path(safe_name).stem
        suffix = Path(safe_name).suffix
        tag = hashlib.sha256(data).hexdigest()[:16]
        dest = upload_root / f"{stem}_{tag}{suffix}"
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(data)

        job_id = store.create_pending(safe_name)
        accepted.append(AsyncUploadAcceptedItem(job_id=job_id, source_name=safe_name))
        spawn_ingestion_thread(tenant_id, job_id, dest, safe_name, st)

    if not accepted:
        raise HTTPException(400, "No valid files.")
    return accepted


@router.post("/text/async", response_model=list[AsyncUploadAcceptedItem], status_code=202)
async def upload_text_async(
    body: TextPasteRequest,
    tenant_id: str = Depends(get_tenant_id),
) -> list[AsyncUploadAcceptedItem]:
    """Paste plain text; stored as UTF-8 .txt and indexed like a file upload."""
    settings = get_settings()
    raw = body.text.encode("utf-8")
    max_b = settings.max_upload_mb * 1024 * 1024
    if len(raw) > max_b:
        raise HTTPException(413, f"Content exceeds {settings.max_upload_mb} MB limit.")
    safe_name = _safe_txt_filename(body.title, "Pasted_text")
    upload_root = tenant_upload_dir(tenant_id)
    stem = Path(safe_name).stem
    suffix = ".txt"
    tag = hashlib.sha256(raw).hexdigest()[:16]
    dest = upload_root / f"{stem}_{tag}{suffix}"
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(raw)

    store = get_job_store(tenant_id)
    job_id = store.create_pending(safe_name)
    spawn_ingestion_thread(tenant_id, job_id, dest, safe_name, SourceType.txt)
    return [AsyncUploadAcceptedItem(job_id=job_id, source_name=safe_name)]


@router.post("/url/async", response_model=list[AsyncUploadAcceptedItem], status_code=202)
async def upload_url_async(
    body: UrlFetchRequest,
    tenant_id: str = Depends(get_tenant_id),
) -> list[AsyncUploadAcceptedItem]:
    """Fetch a URL (HTML or plain text), extract text, then index as .txt."""
    url = body.url.strip()
    if not is_safe_http_url(url):
        raise HTTPException(400, "URL not allowed (blocked for security). Use a public http(s) URL.")

    try:
        _final, stem, text = await fetch_url_content(url)
    except httpx.HTTPError as e:
        raise HTTPException(502, f"Could not fetch URL: {e!s}") from e
    except ValueError as e:
        raise HTTPException(400, str(e)) from e

    settings = get_settings()
    raw = text.encode("utf-8")
    max_b = settings.max_upload_mb * 1024 * 1024
    if len(raw) > max_b:
        raise HTTPException(413, f"Extracted text exceeds {settings.max_upload_mb} MB limit.")

    safe_name = f"{stem}.txt"
    upload_root = tenant_upload_dir(tenant_id)
    tag = hashlib.sha256(raw).hexdigest()[:16]
    dest = upload_root / f"{stem}_{tag}.txt"
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(raw)

    store = get_job_store(tenant_id)
    job_id = store.create_pending(safe_name)
    spawn_ingestion_thread(tenant_id, job_id, dest, safe_name, SourceType.txt)
    return [AsyncUploadAcceptedItem(job_id=job_id, source_name=safe_name)]
