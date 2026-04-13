"""Wire ingestion → chunking → FAISS."""
from pathlib import Path

from app.ingestion import extract_text_for_source
from app.ingestion.chunking import text_to_documents
from app.ingestion.registry import get_registry
from app.models.schemas import SourceType, UploadResponse
from app.retrieval.faiss_store import get_faiss_manager


def process_upload(
    tenant_id: str,
    saved_path: Path,
    original_name: str,
    source_type: SourceType,
) -> UploadResponse:
    """
    Register document, extract, chunk, index. Rolls back registry entry if indexing fails
    before a consistent vector write (best-effort; see FAISS notes in README).
    """
    registry = get_registry(tenant_id)
    rec = registry.create(
        source_name=original_name,
        source_type=source_type,
        file_path=str(saved_path),
        extra_metadata={"size_bytes": saved_path.stat().st_size},
    )
    try:
        text = extract_text_for_source(saved_path, source_type)
        extra: dict = {}
        if source_type == SourceType.video:
            extra["modality"] = "video_transcript_and_optional_frame"
        elif source_type == SourceType.image:
            extra["modality"] = "ocr_and_vision"

        docs = text_to_documents(
            text,
            document_id=rec.document_id,
            source_name=original_name,
            source_type=source_type,
            base_metadata=extra,
        )
        n = get_faiss_manager(tenant_id).add_documents(docs)
        return UploadResponse(
            document_id=rec.document_id,
            source_name=original_name,
            source_type=source_type,
            chunks_indexed=n,
            message=f"Indexed {n} chunks.",
        )
    except Exception:
        registry.delete(rec.document_id)
        raise
