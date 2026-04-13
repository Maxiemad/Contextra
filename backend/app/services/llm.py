"""Chat LLM factory: OpenAI, Hugging Face Inference, or free local Ollama."""
from __future__ import annotations

import os

from langchain_core.language_models.chat_models import BaseChatModel

from app.config import get_settings


def _hf_token() -> str:
    s = get_settings()
    return (s.huggingfacehub_api_token or os.getenv("HF_TOKEN") or os.getenv("HUGGINGFACEHUB_API_TOKEN") or "").strip()


def is_llm_configured() -> bool:
    """Whether /query may attempt an LLM call (Ollama needs no keys)."""
    s = get_settings()
    mode = (s.llm_backend or "auto").lower()
    if mode == "openai":
        return bool(s.openai_api_key)
    if mode == "huggingface":
        return bool(_hf_token())
    if mode == "ollama":
        return True
    # auto: OpenAI, else HF token, else free local Ollama (always allowed to try)
    return True


def get_chat_llm() -> BaseChatModel:
    settings = get_settings()
    mode = (settings.llm_backend or "auto").lower()
    if mode == "auto":
        if settings.openai_api_key:
            mode = "openai"
        elif _hf_token():
            mode = "huggingface"
        else:
            mode = "ollama"

    if mode == "openai":
        if not settings.openai_api_key:
            raise RuntimeError("OPENAI_API_KEY is required when LLM_BACKEND=openai.")
        from langchain_openai import ChatOpenAI

        return ChatOpenAI(
            model=settings.openai_chat_model,
            api_key=settings.openai_api_key,
            base_url=settings.openai_base_url,
            temperature=0.2,
        )

    if mode == "huggingface":
        token = _hf_token()
        if not token:
            raise RuntimeError(
                "Hugging Face token required: set HUGGINGFACEHUB_API_TOKEN or HF_TOKEN when LLM_BACKEND=huggingface."
            )
        from langchain_huggingface import ChatHuggingFace
        from langchain_huggingface.llms import HuggingFaceEndpoint

        llm = HuggingFaceEndpoint(
            repo_id=settings.hf_chat_repo_id,
            huggingfacehub_api_token=token,
            task="text-generation",
            max_new_tokens=1024,
            temperature=0.2,
            do_sample=True,
        )
        return ChatHuggingFace(llm=llm)

    if mode == "ollama":
        from langchain_ollama import ChatOllama

        return ChatOllama(
            model=settings.ollama_model,
            base_url=settings.ollama_base_url,
            temperature=0.2,
        )

    raise RuntimeError(
        f"Unknown LLM_BACKEND: {settings.llm_backend!r} (use auto, openai, huggingface, ollama)"
    )
