"""GET /sources, DELETE /sources/{document_id}"""
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException

from app.deps import get_tenant_id
from app.ingestion.registry import get_registry
from app.models.schemas import SourceListItem
from app.retrieval.faiss_store import get_faiss_manager

router = APIRouter(prefix="/sources", tags=["sources"])


@router.get("", response_model=list[SourceListItem])
async def list_sources(tenant_id: str = Depends(get_tenant_id)) -> list[SourceListItem]:
    reg = get_registry(tenant_id)
    items: list[SourceListItem] = []
    for d in reg.list_all():
        items.append(
            SourceListItem(
                document_id=d.document_id,
                source_name=d.source_name,
                source_type=d.source_type,
                created_at=d.created_at,
            )
        )
    items.sort(key=lambda x: x.created_at, reverse=True)
    return items


@router.delete("/{document_id}")
async def delete_source(document_id: str, tenant_id: str = Depends(get_tenant_id)) -> dict:
    """Remove a source from the registry, delete its vectors, and remove the uploaded file."""
    reg = get_registry(tenant_id)
    rec = reg.get(document_id)
    if not rec:
        raise HTTPException(404, "Document not found.")
    fp = Path(rec.file_path)
    if fp.is_file():
        try:
            fp.unlink()
        except OSError:
            pass
    reg.delete(document_id)
    get_faiss_manager(tenant_id).delete_by_document_id(document_id)
    return {"ok": True, "document_id": document_id}
