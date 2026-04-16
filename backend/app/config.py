"""Application configuration from environment."""
from functools import lru_cache
from pathlib import Path

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # --- LLM selection ---
    # auto = Ollama if reachable, else Groq
    llm_backend: str = "auto"  # auto | ollama | groq

    # Groq (https://console.groq.com/keys) — cloud fallback
    groq_api_key: str = ""
    groq_chat_model: str = "llama-3.3-70b-versatile"

    # Ollama (https://ollama.com/) — local primary
    ollama_base_url: str = "http://127.0.0.1:11434"
    ollama_model: str = "llama3.2"
    ollama_vision_model: str = "llava"
    ollama_vision_timeout_sec: int = 90
    use_ollama_vision: bool = True

    # --- Embeddings (always local) ---
    st_model_name: str = "all-MiniLM-L6-v2"
    # kept for backward-compat with older .env files; no longer consulted
    use_sentence_transformers: bool = True

    # --- Storage ---
    data_root: Path | None = None

    @field_validator("data_root", mode="before")
    @classmethod
    def _empty_data_root(cls, v: object) -> object:
        if v is None or v == "":
            return None
        return v

    @property
    def data_dir(self) -> Path:
        if self.data_root is not None:
            return Path(self.data_root).expanduser().resolve()
        return Path(__file__).resolve().parent.parent.parent / "data"

    # --- Auth ---
    api_key: str = ""

    # --- Limits ---
    default_top_k: int = 5
    max_upload_mb: int = 100

    # --- CORS ---
    # Comma-separated explicit origins. Use FRONTEND_URL for the deployed UI,
    # plus localhost variants for dev. Avoid "*" in production when credentials are used.
    frontend_url: str = ""
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"


@lru_cache
def get_settings() -> Settings:
    s = Settings()
    try:
        s.data_dir.mkdir(parents=True, exist_ok=True)
    except OSError:
        # Read-only FS edge case on some hosts — let request-time code surface it
        pass
    return s