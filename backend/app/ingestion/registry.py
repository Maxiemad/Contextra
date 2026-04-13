"""JSON-backed document registry (per tenant)."""
import json
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock
from typing import Any
from uuid import uuid4

from app.models.schemas import DocumentRecord, SourceType
from app.tenant_paths import tenant_data_dir


class DocumentRegistry:
    """Thread-safe registry of uploaded documents."""

    def __init__(self, tenant_id: str) -> None:
        self._tenant_id = tenant_id
        self._path = tenant_data_dir(tenant_id) / "registry.json"
        self._lock = Lock()
        self._docs: dict[str, dict[str, Any]] = {}
        self._load()

    def _load(self) -> None:
        if self._path.exists():
            with open(self._path, encoding="utf-8") as f:
                data = json.load(f)
                self._docs = data.get("documents", {})

    def _save(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        with open(self._path, "w", encoding="utf-8") as f:
            json.dump({"documents": self._docs}, f, indent=2, default=str)

    def create(
        self,
        source_name: str,
        source_type: SourceType,
        file_path: str,
        extra_metadata: dict[str, Any] | None = None,
    ) -> DocumentRecord:
        with self._lock:
            doc_id = str(uuid4())
            rec = DocumentRecord(
                document_id=doc_id,
                source_name=source_name,
                source_type=source_type,
                created_at=datetime.now(timezone.utc),
                file_path=file_path,
                extra_metadata=extra_metadata or {},
            )
            self._docs[doc_id] = rec.model_dump(mode="json")
            self._save()
            return rec

    def get(self, document_id: str) -> DocumentRecord | None:
        with self._lock:
            raw = self._docs.get(document_id)
            if not raw:
                return None
            return DocumentRecord.model_validate(raw)

    def list_all(self) -> list[DocumentRecord]:
        with self._lock:
            return [DocumentRecord.model_validate(v) for v in self._docs.values()]

    def delete(self, document_id: str) -> bool:
        with self._lock:
            if document_id not in self._docs:
                return False
            del self._docs[document_id]
            self._save()
            return True


_registries: dict[str, DocumentRegistry] = {}
_reg_lock = Lock()


def get_registry(tenant_id: str) -> DocumentRegistry:
    with _reg_lock:
        if tenant_id not in _registries:
            _registries[tenant_id] = DocumentRegistry(tenant_id)
        return _registries[tenant_id]
