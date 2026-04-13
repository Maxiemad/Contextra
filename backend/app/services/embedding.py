"""Embeddings: OpenAI or SentenceTransformers."""
from functools import lru_cache

from langchain_core.embeddings import Embeddings

from app.config import get_settings


class _STEmbeddings(Embeddings):
    """SentenceTransformers wrapper for LangChain."""

    def __init__(self, model_name: str) -> None:
        from sentence_transformers import SentenceTransformer

        self._model = SentenceTransformer(model_name)

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return self._model.encode(texts, convert_to_numpy=True).tolist()

    def embed_query(self, text: str) -> list[float]:
        return self._model.encode([text], convert_to_numpy=True)[0].tolist()


@lru_cache
def get_embeddings() -> Embeddings:
    settings = get_settings()
    if settings.openai_api_key and not settings.use_sentence_transformers:
        from langchain_openai import OpenAIEmbeddings

        return OpenAIEmbeddings(
            model=settings.openai_embedding_model,
            openai_api_key=settings.openai_api_key,
            openai_api_base=settings.openai_base_url,
        )
    return _STEmbeddings(settings.st_model_name)
