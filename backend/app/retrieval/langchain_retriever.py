"""LangChain retriever wrapping FAISS top-K + scores (scores exposed via run_manager optional metadata)."""
from __future__ import annotations

from langchain_core.callbacks import CallbackManagerForRetrieverRun
from langchain_core.documents import Document
from langchain_core.retrievers import BaseRetriever
from pydantic import Field

from app.retrieval.faiss_store import get_faiss_manager


class TopKFaissRetriever(BaseRetriever):
    """Strict top-K similarity retrieval; no reranking or query expansion."""

    k: int = Field(default=5, ge=1, le=50)
    document_ids: list[str] | None = None
    tenant_id: str = Field(default="default")

    def _get_relevant_documents(
        self,
        query: str,
        *,
        run_manager: CallbackManagerForRetrieverRun,
    ) -> list[Document]:
        store = get_faiss_manager(self.tenant_id)
        pairs = store.similarity_search_top_k(query, k=self.k, document_ids=self.document_ids)
        return [doc for doc, _ in pairs]

    def retrieve_with_scores(self, query: str) -> list[tuple[Document, float]]:
        store = get_faiss_manager(self.tenant_id)
        return store.similarity_search_top_k(query, k=self.k, document_ids=self.document_ids)
