"""Persistent ingestion job queue state (per tenant)."""
from __future__ import annotations

import json
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from app.models.schemas import IngestionJobResponse, JobStatus, UploadResponse
from app.tenant_paths import tenant_data_dir


class IngestionJobStore:
    def __init__(self, tenant_id: str) -> None:
        self._tenant_id = tenant_id
        self._path = tenant_data_dir(tenant_id) / "ingestion_jobs.json"
        self._lock = threading.Lock()
        self._jobs: dict[str, dict[str, Any]] = {}
        self._load()

    def _load(self) -> None:
        if self._path.exists():
            with open(self._path, encoding="utf-8") as f:
                data = json.load(f)
                self._jobs = data.get("jobs", {})

    def _save(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        with open(self._path, "w", encoding="utf-8") as f:
            json.dump({"jobs": self._jobs}, f, indent=2, default=str)

    def create_pending(self, source_name: str) -> str:
        job_id = str(uuid4())
        now = datetime.now(timezone.utc)
        with self._lock:
            self._jobs[job_id] = {
                "job_id": job_id,
                "status": JobStatus.pending.value,
                "source_name": source_name,
                "created_at": now.isoformat(),
                "updated_at": now.isoformat(),
                "error": None,
                "result": None,
            }
            self._save()
        return job_id

    def update_running(self, job_id: str) -> None:
        now = datetime.now(timezone.utc)
        with self._lock:
            if job_id not in self._jobs:
                return
            self._jobs[job_id]["status"] = JobStatus.running.value
            self._jobs[job_id]["updated_at"] = now.isoformat()
            self._save()

    def complete(self, job_id: str, result: UploadResponse) -> None:
        now = datetime.now(timezone.utc)
        with self._lock:
            if job_id not in self._jobs:
                return
            self._jobs[job_id]["status"] = JobStatus.completed.value
            self._jobs[job_id]["result"] = result.model_dump(mode="json")
            self._jobs[job_id]["error"] = None
            self._jobs[job_id]["updated_at"] = now.isoformat()
            self._save()

    def fail(self, job_id: str, message: str) -> None:
        now = datetime.now(timezone.utc)
        with self._lock:
            if job_id not in self._jobs:
                return
            self._jobs[job_id]["status"] = JobStatus.failed.value
            self._jobs[job_id]["error"] = message
            self._jobs[job_id]["result"] = None
            self._jobs[job_id]["updated_at"] = now.isoformat()
            self._save()

    def get_public(self, job_id: str) -> IngestionJobResponse | None:
        with self._lock:
            raw = self._jobs.get(job_id)
            if not raw:
                return None
        res = None
        if raw.get("result"):
            res = UploadResponse.model_validate(raw["result"])

        def _parse_iso(s: str) -> datetime:
            if s.endswith("Z"):
                s = s[:-1] + "+00:00"
            return datetime.fromisoformat(s)

        return IngestionJobResponse(
            job_id=raw["job_id"],
            status=JobStatus(raw["status"]),
            source_name=raw["source_name"],
            created_at=_parse_iso(raw["created_at"]),
            updated_at=_parse_iso(raw["updated_at"]),
            error=raw.get("error"),
            result=res,
        )


_stores: dict[str, IngestionJobStore] = {}
_store_lock = threading.Lock()


def get_job_store(tenant_id: str) -> IngestionJobStore:
    with _store_lock:
        if tenant_id not in _stores:
            _stores[tenant_id] = IngestionJobStore(tenant_id)
        return _stores[tenant_id]
