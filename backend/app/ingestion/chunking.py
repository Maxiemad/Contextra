"""Semantic-aware chunking: target 300–800 tokens with overlap."""
from __future__ import annotations

import re
from uuid import uuid4

import tiktoken
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.models.schemas import SourceType

# Target ~400–600 tokens per chunk, overlap ~80–120 tokens
DEFAULT_CHUNK_TOKENS = 512
DEFAULT_OVERLAP_TOKENS = 96
MIN_CHUNK_TOKENS = 300
MAX_CHUNK_TOKENS = 800


def _encoding():
    return tiktoken.get_encoding("cl100k_base")


def token_length(text: str) -> int:
    return len(_encoding().encode(text))


def split_paragraphs(text: str) -> list[str]:
    """Split on blank lines; keep non-empty blocks."""
    parts = re.split(r"\n\s*\n+", text.strip())
    return [p.strip() for p in parts if p.strip()]


def merge_paragraphs_semantic(paragraphs: list[str]) -> list[str]:
    """
    Greedy merge paragraphs into chunks between MIN and MAX token counts where possible.
    """
    if not paragraphs:
        return []
    chunks: list[str] = []
    buf: list[str] = []
    buf_tokens = 0

    for para in paragraphs:
        t = token_length(para)
        if t > MAX_CHUNK_TOKENS:
            if buf:
                chunks.append("\n\n".join(buf))
                buf = []
                buf_tokens = 0
            # Oversized paragraph: split with recursive splitter
            sub = RecursiveCharacterTextSplitter.from_tiktoken_encoder(
                chunk_size=DEFAULT_CHUNK_TOKENS,
                chunk_overlap=DEFAULT_OVERLAP_TOKENS,
                encoding_name="cl100k_base",
            ).split_text(para)
            chunks.extend(sub)
            continue

        if buf_tokens + t > MAX_CHUNK_TOKENS and buf:
            chunks.append("\n\n".join(buf))
            # Overlap: start next chunk with last paragraph if small overlap helps
            overlap_para = buf[-1] if buf and token_length(buf[-1]) < DEFAULT_OVERLAP_TOKENS * 2 else None
            buf = [overlap_para, para] if overlap_para else [para]
            buf_tokens = sum(token_length(x) for x in buf)
        else:
            buf.append(para)
            buf_tokens += t
            if buf_tokens >= MIN_CHUNK_TOKENS:
                chunks.append("\n\n".join(buf))
                buf = []
                buf_tokens = 0

    if buf:
        chunks.append("\n\n".join(buf))

    return chunks


def text_to_documents(
    full_text: str,
    document_id: str,
    source_name: str,
    source_type: SourceType,
    base_metadata: dict | None = None,
) -> list[Document]:
    """Turn extracted text into LangChain Documents with chunk_id and indices."""
    base = base_metadata or {}
    paragraphs = split_paragraphs(full_text) or ([full_text.strip()] if full_text.strip() else [])
    if not paragraphs:
        return []

    raw_chunks = merge_paragraphs_semantic(paragraphs)
    if not raw_chunks and full_text.strip():
        raw_chunks = RecursiveCharacterTextSplitter.from_tiktoken_encoder(
            chunk_size=DEFAULT_CHUNK_TOKENS,
            chunk_overlap=DEFAULT_OVERLAP_TOKENS,
            encoding_name="cl100k_base",
        ).split_text(full_text)

    docs: list[Document] = []
    for idx, chunk_text in enumerate(raw_chunks):
        chunk_id = str(uuid4())
        meta = {
            "document_id": document_id,
            "chunk_id": chunk_id,
            "source_name": source_name,
            "source_type": source_type.value,
            "chunk_index": idx,
            **base,
        }
        docs.append(Document(page_content=chunk_text, metadata=meta))
    return docs
