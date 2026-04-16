"""Embeddings: local SentenceTransformers only.

Model: all-MiniLM-L6-v2 (~90 MB, 384-dim). Downloaded on first use and
cached by huggingface_hub to ~/.cache/huggingface. On Render, set
SENTENCE_TRANSFORMERS_HOME=/tmp/st_cache to survive between requests.
"""
from __future__ import annotations

import logging
from functools import lru_cache

from langchain_core.embeddings import Embeddings

from app.config import get_settings

logger = logging.getLogger(__name__)


class _STEmbeddings(Embeddings):
    """SentenceTransformers wrapper for LangChain."""

    def __init__(self, model_name: str) -> None:
        from sentence_transformers import SentenceTransformer
        logger.info("Loading SentenceTransformer model: %s", model_name)
        self._model = SentenceTransformer(model_name)
        logger.info("SentenceTransformer model loaded.")

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return self._model.encode(texts, convert_to_numpy=True).tolist()

    def embed_query(self, text: str) -> list[float]:
        return self._model.encode([text], convert_to_numpy=True)[0].tolist()


@lru_cache(maxsize=1)
def get_embeddings() -> Embeddings:
    settings = get_settings()
    model_name = settings.st_model_name or "all-MiniLM-L6-v2"
    return _STEmbeddings(model_name)