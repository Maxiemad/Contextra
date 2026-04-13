"""FAISS vector store with persistence and top-K similarity retrieval only."""
from __future__ import annotations

import json
import shutil
from threading import RLock
from typing import Any

from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document

from app.services.embedding import get_embeddings
from app.tenant_paths import tenant_data_dir

INDEX_NAME = "multimodal_rag"
META_NAME = "chunk_store.json"


class FaissIndexManager:
    """
    Single-process FAISS index with JSON sidecar for authoritative chunk text
    (ensures long excerpts for citations).
    """

    def __init__(self, tenant_id: str) -> None:
        self._tenant_id = tenant_id
        self._lock = RLock()
        self._faiss: FAISS | None = None
        self._chunk_texts: dict[str, str] = {}
        self._index_dir = tenant_data_dir(tenant_id) / "faiss"
        self._sidecar_path = self._index_dir / META_NAME
        self._load_or_init()

    def _load_or_init(self) -> None:
        emb = get_embeddings()
        faiss_marker = self._index_dir / f"{INDEX_NAME}.faiss"
        if faiss_marker.exists():
            self._faiss = FAISS.load_local(
                str(self._index_dir),
                emb,
                allow_dangerous_deserialization=True,
                index_name=INDEX_NAME,
            )
            if self._sidecar_path.exists():
                with open(self._sidecar_path, encoding="utf-8") as f:
                    data = json.load(f)
                    self._chunk_texts = data.get("chunks", {})

    def _persist(self) -> None:
        if self._faiss is None:
            return
        self._index_dir.mkdir(parents=True, exist_ok=True)
        self._faiss.save_local(str(self._index_dir), index_name=INDEX_NAME)
        with open(self._sidecar_path, "w", encoding="utf-8") as f:
            json.dump({"chunks": self._chunk_texts}, f)

    def _all_documents(self) -> list[Document]:
        if self._faiss is None:
            return []
        store = getattr(self._faiss.docstore, "_dict", {})
        return [doc for doc in store.values() if isinstance(doc, Document)]

    def add_documents(self, documents: list[Document]) -> int:
        if not documents:
            return 0
        emb = get_embeddings()
        with self._lock:
            if self._faiss is None:
                self._faiss = FAISS.from_documents(documents, emb)
            else:
                self._faiss.add_documents(documents)
            for d in documents:
                cid = d.metadata.get("chunk_id")
                if cid:
                    self._chunk_texts[str(cid)] = d.page_content
            self._persist()
        return len(documents)

    def _wipe_persisted_index(self) -> None:
        """Remove on-disk FAISS files so an empty index does not reload old vectors."""
        if self._index_dir.exists():
            shutil.rmtree(self._index_dir, ignore_errors=True)
        self._index_dir.mkdir(parents=True, exist_ok=True)
        self._sidecar_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self._sidecar_path, "w", encoding="utf-8") as f:
            json.dump({"chunks": {}}, f)

    def delete_by_document_id(self, document_id: str) -> int:
        """Rebuild index excluding chunks for document_id."""
        with self._lock:
            kept = [d for d in self._all_documents() if d.metadata.get("document_id") != document_id]
            new_sidecar: dict[str, str] = {}
            for d in kept:
                cid = d.metadata.get("chunk_id")
                if cid:
                    new_sidecar[str(cid)] = self._chunk_texts.get(str(cid), d.page_content)
            self._chunk_texts = new_sidecar
            emb = get_embeddings()
            if not kept:
                self._faiss = None
                self._wipe_persisted_index()
            else:
                self._faiss = FAISS.from_documents(kept, emb)
                self._persist()
            return len(kept)

    def similarity_search_top_k(
        self,
        query: str,
        k: int,
        document_ids: list[str] | None = None,
    ) -> list[tuple[Document, float]]:
        if self._faiss is None:
            return []
        fetch_k = max(k * 5, k + 5, 10)
        with self._lock:
            pairs = self._faiss.similarity_search_with_score(query, k=fetch_k)

        filt: set[str] | None = set(document_ids) if document_ids else None
        results: list[tuple[Document, float]] = []
        for doc, dist in pairs:
            if filt and doc.metadata.get("document_id") not in filt:
                continue
            sim = 1.0 / (1.0 + float(dist))
            cid = doc.metadata.get("chunk_id")
            if cid and str(cid) in self._chunk_texts:
                doc = Document(
                    page_content=self._chunk_texts[str(cid)],
                    metadata=dict(doc.metadata),
                )
            results.append((doc, sim))
            if len(results) >= k:
                break
        return results[:k]

    def get_chunks_for_document(self, document_id: str) -> list[dict[str, Any]]:
        out: list[dict[str, Any]] = []
        for doc in self._all_documents():
            if doc.metadata.get("document_id") != document_id:
                continue
            cid = doc.metadata.get("chunk_id")
            text = doc.page_content
            if cid and str(cid) in self._chunk_texts:
                text = self._chunk_texts[str(cid)]
            out.append(
                {
                    "chunk_id": str(cid),
                    "document_id": document_id,
                    "chunk_index": doc.metadata.get("chunk_index"),
                    "text": text,
                    "source_name": doc.metadata.get("source_name"),
                }
            )
        out.sort(key=lambda x: (x.get("chunk_index") is None, x.get("chunk_index", 0)))
        return out


_managers: dict[str, FaissIndexManager] = {}
_mgr_lock = RLock()


def get_faiss_manager(tenant_id: str) -> FaissIndexManager:
    with _mgr_lock:
        if tenant_id not in _managers:
            _managers[tenant_id] = FaissIndexManager(tenant_id)
        return _managers[tenant_id]
