"""Pydantic models for API and internal types."""
from datetime import datetime
from enum import Enum
from typing import Any
from pydantic import BaseModel, Field


class SourceType(str, Enum):
    pdf = "pdf"
    docx = "docx"
    txt = "txt"
    image = "image"
    video = "video"


class DocumentRecord(BaseModel):
    """Registered uploaded source."""

    document_id: str
    source_name: str
    source_type: SourceType
    created_at: datetime
    file_path: str
    extra_metadata: dict[str, Any] = Field(default_factory=dict)


class ChunkRecord(BaseModel):
    """Single chunk with traceability fields."""

    chunk_id: str
    document_id: str
    source_name: str
    source_type: SourceType
    text: str
    chunk_index: int
    metadata: dict[str, Any] = Field(default_factory=dict)


class Citation(BaseModel):
    """Citation attached to an answer."""

    document_id: str
    chunk_id: str
    source_name: str
    source_type: SourceType
    similarity_score: float
    excerpt: str = Field(description="Exact retrieved text used as context")
    chunk_index: int | None = None


class TextPasteRequest(BaseModel):
    """Paste raw text as a .txt source."""

    text: str = Field(..., min_length=1, max_length=50_000_000)
    title: str | None = Field(default=None, max_length=200)


class UrlFetchRequest(BaseModel):
    """Fetch a public URL and index extracted text (HTML → text)."""

    url: str = Field(..., min_length=8, max_length=2048)


class QueryRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=16_000)
    top_k: int | None = Field(default=None, ge=1, le=50)
    document_ids: list[str] | None = Field(
        default=None,
        description="If set, restrict retrieval to these documents",
    )
    response_format: str | None = Field(
        default=None,
        description="Optional hint: bullets, table, sections, or default prose",
    )


class QueryResponse(BaseModel):
    answer: str
    citations: list[Citation]
    retrieved_chunks_preview: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Sanitized chunk info for UI",
    )


class SourceListItem(BaseModel):
    document_id: str
    source_name: str
    source_type: SourceType
    created_at: datetime


class UploadResponse(BaseModel):
    document_id: str
    source_name: str
    source_type: SourceType
    chunks_indexed: int
    message: str


class JobStatus(str, Enum):
    pending = "pending"
    running = "running"
    completed = "completed"
    failed = "failed"


class AsyncUploadAcceptedItem(BaseModel):
    job_id: str
    source_name: str


class IngestionJobResponse(BaseModel):
    job_id: str
    status: JobStatus
    source_name: str
    created_at: datetime
    updated_at: datetime
    error: str | None = None
    result: UploadResponse | None = None
