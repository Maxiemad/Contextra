"""GET /jobs/{job_id} — ingestion job status."""
from fastapi import APIRouter, Depends, HTTPException

from app.deps import get_tenant_id
from app.models.schemas import IngestionJobResponse
from app.services.ingestion_jobs import get_job_store

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.get("/{job_id}", response_model=IngestionJobResponse)
async def get_job(
    job_id: str,
    tenant_id: str = Depends(get_tenant_id),
) -> IngestionJobResponse:
    store = get_job_store(tenant_id)
    rec = store.get_public(job_id)
    if not rec:
        raise HTTPException(404, "Job not found.")
    return rec
