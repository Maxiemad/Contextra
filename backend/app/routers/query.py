"""POST /query"""
from fastapi import APIRouter, Depends, HTTPException

from app.deps import get_tenant_id
from app.models.schemas import QueryRequest, QueryResponse
from app.orchestration.pipeline import run_query
from app.services.llm import is_llm_configured

router = APIRouter(prefix="/query", tags=["query"])


@router.post("", response_model=QueryResponse)
async def query(
    req: QueryRequest,
    tenant_id: str = Depends(get_tenant_id),
) -> QueryResponse:
    if not is_llm_configured():
        raise HTTPException(
            503,
            "No LLM configured for this LLM_BACKEND. For free local chat install Ollama and use "
            "LLM_BACKEND=ollama or leave LLM_BACKEND=auto with no paid keys (defaults to Ollama).",
        )
    return run_query(
        query=req.query,
        tenant_id=tenant_id,
        top_k=req.top_k,
        document_ids=req.document_ids,
        response_format=req.response_format,
    )
