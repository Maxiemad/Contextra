"""
Orchestration pipeline (LangChain composition):
1. Receive query
2. Top-K retrieval with similarity scores
3. ChatPromptTemplate + LLM + string output
4. Citations from retrieved chunks
"""
from __future__ import annotations

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate

from app.config import get_settings
from app.models.schemas import Citation, QueryResponse, SourceType
from app.retrieval.langchain_retriever import TopKFaissRetriever
from app.services.llm import get_chat_llm

SYSTEM_BASE = """You are a careful research assistant. Answer ONLY using the provided CONTEXT.
If the context is insufficient, say so clearly.
Always ground claims in the context. When listing facts, tie them to sources implicitly via the citation list the system provides.
For summaries: be concise and structured when asked for bullets, tables, or sections.

Multimodal: CONTEXT may include "## OCR Text", "## Visual / Semantic Description (Ollama)", or "(OpenAI)" — those lines ARE the image description produced by tools (not raw pixels). For questions like "what is in the image", summarize and quote from those sections. Do NOT say you cannot see images or that the user must install Tesseract/OpenAI if those sections already describe the image. If CONTEXT only contains a short bracketed message that indexing failed, say the image must be re-uploaded after vision (Ollama llava) is configured — do not invent other excuses."""

PROMPT = ChatPromptTemplate.from_messages(
    [
        ("system", SYSTEM_BASE),
        (
            "human",
            """{instructions}

USER QUESTION:
{query}

CONTEXT (authoritative; do not invent facts beyond it):
{context}
""",
        ),
    ]
)


def _format_instructions(response_format: str | None) -> str:
    if not response_format:
        return "Respond in clear prose with short paragraphs."
    rf = response_format.lower()
    if "bullet" in rf:
        return "Format the answer primarily as bullet points."
    if "table" in rf:
        return "Include a Markdown table when comparing items; otherwise bullets."
    if "section" in rf:
        return "Use Markdown headings (##) to separate sections."
    return "Use clear structure (sections or bullets) as appropriate."


def _format_context_block(chunks: list[tuple[object, float]]) -> str:
    lines: list[str] = []
    for i, (doc, score) in enumerate(chunks, start=1):
        meta = doc.metadata  # type: ignore[attr-defined]
        name = meta.get("source_name", "unknown")
        cid = meta.get("chunk_id", "")
        did = meta.get("document_id", "")
        content = doc.page_content  # type: ignore[attr-defined]
        lines.append(
            f"[Context {i}] source={name} document_id={did} chunk_id={cid} similarity={score:.4f}\n"
            f"{str(content).strip()}"
        )
    return "\n\n---\n\n".join(lines)


def run_query(
    query: str,
    tenant_id: str = "default",
    top_k: int | None = None,
    document_ids: list[str] | None = None,
    response_format: str | None = None,
) -> QueryResponse:
    settings = get_settings()
    k = top_k or settings.default_top_k
    retriever = TopKFaissRetriever(k=k, document_ids=document_ids, tenant_id=tenant_id)
    retrieved = retriever.retrieve_with_scores(query)

    citations: list[Citation] = []
    for doc, score in retrieved:
        meta = doc.metadata
        try:
            st = SourceType(meta.get("source_type", "txt"))
        except ValueError:
            st = SourceType.txt
        citations.append(
            Citation(
                document_id=str(meta.get("document_id", "")),
                chunk_id=str(meta.get("chunk_id", "")),
                source_name=str(meta.get("source_name", "")),
                source_type=st,
                similarity_score=float(score),
                excerpt=doc.page_content.strip(),
                chunk_index=meta.get("chunk_index"),
            )
        )

    ctx = _format_context_block(retrieved)
    instructions = _format_instructions(response_format)
    if not ctx.strip():
        ctx = "[No chunks retrieved — say you could not find relevant sources.]"

    def _failed_image_placeholder(text: str) -> bool:
        t = text or ""
        return "[No image description indexed" in t or "[No text extracted from image" in t

    # Stale image index: chunks are only failure placeholders — avoid LLM refusing / Tesseract lecture
    if retrieved and all(_failed_image_placeholder(d.page_content or "") for d, _ in retrieved):
        answer = (
            "This image is still indexed with an old **placeholder** (vision did not run when it was uploaded). "
            "Fix: run `ollama pull llava`, keep Ollama running, restart the backend, "
            "then **remove the source** (× on the left) and **upload the image again** so old vectors are gone. "
            "Then ask again — context should include an Ollama visual description."
        )
        preview = [
            {
                "chunk_id": c.chunk_id,
                "document_id": c.document_id,
                "source_name": c.source_name,
                "similarity_score": c.similarity_score,
                "excerpt": c.excerpt[:2000],
            }
            for c in citations
        ]
        return QueryResponse(answer=answer, citations=citations, retrieved_chunks_preview=preview)

    llm = get_chat_llm()
    chain = PROMPT | llm | StrOutputParser()
    answer = chain.invoke(
        {
            "instructions": instructions,
            "query": query,
            "context": ctx,
        }
    ).strip()

    preview = [
        {
            "chunk_id": c.chunk_id,
            "document_id": c.document_id,
            "source_name": c.source_name,
            "similarity_score": c.similarity_score,
            "excerpt": c.excerpt[:2000],
        }
        for c in citations
    ]

    return QueryResponse(
        answer=answer,
        citations=citations,
        retrieved_chunks_preview=preview,
    )
