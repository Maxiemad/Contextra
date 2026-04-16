"""LLM factory with runtime Ollama → Groq fallback.

Behavior:
  - LLM_BACKEND=ollama  → Ollama only
  - LLM_BACKEND=groq    → Groq only
  - LLM_BACKEND=auto (default):
        If Ollama is reachable (OLLAMA_BASE_URL responds within OLLAMA_PROBE_TIMEOUT),
        use Ollama. Otherwise fall back to Groq (GROQ_API_KEY required).

Public API (unchanged, so pipeline.py keeps working):
    get_llm()       -> (kind, runnable)   # kind is always "chat" now
    get_chat_llm()  -> BaseChatModel
    is_llm_configured() -> bool
"""
from __future__ import annotations

import logging
import os
from functools import lru_cache

import httpx
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.runnables import Runnable

from app.config import get_settings

logger = logging.getLogger(__name__)

# Probe timeout for Ollama reachability check (seconds)
_OLLAMA_PROBE_TIMEOUT = float(os.getenv("OLLAMA_PROBE_TIMEOUT", "1.5"))
# Request timeout when actually calling the LLM (seconds)
_LLM_REQUEST_TIMEOUT = float(os.getenv("LLM_REQUEST_TIMEOUT", "60"))


def _groq_key() -> str:
    s = get_settings()
    return (os.getenv("GROQ_API_KEY") or s.groq_api_key or "").strip()


@lru_cache(maxsize=1)
def _ollama_reachable() -> bool:
    """Check once per process whether Ollama is serving.

    Cached so we don't pay the probe cost on every request. If you change
    OLLAMA_BASE_URL at runtime, restart the process.
    """
    s = get_settings()
    url = s.ollama_base_url.rstrip("/") + "/api/tags"
    try:
        r = httpx.get(url, timeout=_OLLAMA_PROBE_TIMEOUT)
        ok = r.status_code == 200
        logger.info("Ollama probe %s -> %s", url, "OK" if ok else f"HTTP {r.status_code}")
        return ok
    except Exception as e:  # noqa: BLE001
        logger.info("Ollama probe %s unreachable: %s", url, e)
        return False


def _resolve_backend() -> str:
    """Decide which backend to use right now."""
    s = get_settings()
    mode = (s.llm_backend or "auto").lower().strip()

    if mode in ("ollama", "groq"):
        return mode

    # auto: prefer local Ollama, fall back to Groq
    if _ollama_reachable():
        return "ollama"
    if _groq_key():
        return "groq"

    # Neither available — surface a clear error at call time
    raise RuntimeError(
        "No LLM backend available. Ollama is unreachable at "
        f"{s.ollama_base_url} and GROQ_API_KEY is not set. "
        "Set GROQ_API_KEY or start Ollama locally."
    )


def is_llm_configured() -> bool:
    s = get_settings()
    mode = (s.llm_backend or "auto").lower()
    if mode == "groq":
        return bool(_groq_key())
    if mode == "ollama":
        return _ollama_reachable()
    # auto
    return _ollama_reachable() or bool(_groq_key())


def _build_ollama() -> BaseChatModel:
    from langchain_ollama import ChatOllama
    s = get_settings()
    logger.info("LLM backend: Ollama (%s @ %s)", s.ollama_model, s.ollama_base_url)
    return ChatOllama(
        model=s.ollama_model,
        base_url=s.ollama_base_url,
        temperature=0.2,
        timeout=_LLM_REQUEST_TIMEOUT,
    )


def _build_groq() -> BaseChatModel:
    from langchain_openai import ChatOpenAI
    s = get_settings()
    key = _groq_key()
    if not key:
        raise RuntimeError("GROQ_API_KEY is required for Groq backend.")
    model = os.getenv("GROQ_CHAT_MODEL") or s.groq_chat_model
    logger.info("LLM backend: Groq (%s)", model)
    return ChatOpenAI(
        model=model,
        api_key=key,
        base_url="https://api.groq.com/openai/v1",
        temperature=0.2,
        max_tokens=1024,
        timeout=_LLM_REQUEST_TIMEOUT,
        max_retries=2,
    )


def get_llm() -> tuple[str, Runnable]:
    """Return (kind, runnable). `kind` is always "chat" now."""
    backend = _resolve_backend()

    if backend == "ollama":
        try:
            return ("chat", _build_ollama())
        except Exception as e:  # noqa: BLE001
            logger.warning("Ollama build failed (%s); falling back to Groq.", e)
            # invalidate probe cache so subsequent calls reflect reality
            _ollama_reachable.cache_clear()
            if _groq_key():
                return ("chat", _build_groq())
            raise

    if backend == "groq":
        return ("chat", _build_groq())

    raise RuntimeError(f"Unsupported LLM backend: {backend!r}")


def get_chat_llm() -> BaseChatModel:
    _, llm = get_llm()
    return llm  # type: ignore[return-value]