"""Background ingestion worker (thread pool)."""
from __future__ import annotations

import threading
from pathlib import Path

from app.models.schemas import SourceType
from app.services.ingestion_jobs import get_job_store
from app.services.upload_service import process_upload


def run_ingestion_job(
    tenant_id: str,
    job_id: str,
    dest: Path,
    safe_name: str,
    source_type: SourceType,
) -> None:
    store = get_job_store(tenant_id)
    store.update_running(job_id)
    try:
        res = process_upload(tenant_id, dest, safe_name, source_type)
        store.complete(job_id, res)
    except Exception as e:
        store.fail(job_id, str(e) or type(e).__name__)


def spawn_ingestion_thread(
    tenant_id: str,
    job_id: str,
    dest: Path,
    safe_name: str,
    source_type: SourceType,
) -> None:
    t = threading.Thread(
        target=run_ingestion_job,
        args=(tenant_id, job_id, dest, safe_name, source_type),
        name=f"ingestion-{job_id[:8]}",
        daemon=True,
    )
    t.start()
