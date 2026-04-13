"""Multimodal ingestion entrypoints."""
from pathlib import Path

from app.models.schemas import SourceType


def extract_text_for_source(path: Path, source_type: SourceType) -> str:
    if source_type == SourceType.pdf:
        from app.ingestion.pdf_ingest import extract_pdf_text

        return extract_pdf_text(path)
    if source_type == SourceType.docx:
        from app.ingestion.docx_ingest import extract_docx_text

        return extract_docx_text(path)
    if source_type == SourceType.txt:
        from app.ingestion.txt_ingest import extract_txt

        return extract_txt(path)
    if source_type == SourceType.image:
        from app.ingestion.image_ingest import extract_image_text

        return extract_image_text(path)
    if source_type == SourceType.video:
        from app.ingestion.video_ingest import extract_video_content

        return extract_video_content(path)
    raise ValueError(f"Unsupported source type: {source_type}")


def guess_source_type(filename: str, content_type: str | None) -> SourceType:
    name = filename.lower()
    ct = (content_type or "").lower()
    if name.endswith(".pdf") or "pdf" in ct:
        return SourceType.pdf
    if name.endswith(".docx") or "wordprocessingml" in ct or "docx" in ct:
        return SourceType.docx
    if name.endswith(".txt") or "text/plain" in ct:
        return SourceType.txt
    if name.endswith((".png", ".jpg", ".jpeg", ".webp")) or "image/" in ct:
        return SourceType.image
    if name.endswith((".mp4", ".mov", ".webm", ".mkv")) or "video/" in ct:
        return SourceType.video
    return SourceType.txt
