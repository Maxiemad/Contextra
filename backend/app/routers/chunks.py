"""GET /chunks/{doc_id}"""
from fastapi import APIRouter, Depends, HTTPException

from app.deps import get_tenant_id
from app.ingestion.registry import get_registry
from app.retrieval.faiss_store import get_faiss_manager

router = APIRouter(prefix="/chunks", tags=["chunks"])


@router.get("/{doc_id}")
async def get_chunks(
    doc_id: str,
    tenant_id: str = Depends(get_tenant_id),
) -> dict:
    reg = get_registry(tenant_id)
    if not reg.get(doc_id):
        raise HTTPException(404, "Document not found.")
    chunks = get_faiss_manager(tenant_id).get_chunks_for_document(doc_id)
    return {"document_id": doc_id, "chunks": chunks}
