"""Application settings, loaded from environment variables and backend/.env.

All secrets (the Hugging Face token) live ONLY here, on the server side.
"""
from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# backend/.env, resolved relative to this file so it works from any working directory.
_ENV_FILE = Path(__file__).resolve().parent.parent / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(_ENV_FILE), env_file_encoding="utf-8", extra="ignore"
    )

    # --- Which engine answers: "local" (Transformers, runs on this machine) or "huggingface" (remote API) ---
    llm_backend: Literal["server", "local", "huggingface"] = "server"

    # --- Local OpenAI-compatible server (llama.cpp `llama-server`, Ollama, LM Studio...) ---
    server_base_url: str = "http://127.0.0.1:8080/v1"
    server_model: str = "qwen3.5-9b"  # llama-server accepts any name; Ollama needs the real model tag
    server_api_key: str = ""  # optional
    server_disable_thinking: bool = True  # sends chat_template_kwargs.enable_thinking=false (Qwen3.x)
    server_max_new_tokens: int = Field(700, ge=50, le=4000)  # Bangla uses many tokens, so keep this generous
    server_timeout_seconds: float = Field(180.0, gt=0)

    # --- Local model (Transformers, e.g. MedGemma) ---
    local_model_id: str = "google/medgemma-1.5-4b-it"
    local_dtype: Literal["bfloat16", "float16", "float32"] = "bfloat16"
    local_max_new_tokens: int = Field(350, ge=50, le=2000)
    local_timeout_seconds: float = Field(180.0, gt=0)

    # --- Hugging Face remote API (also its token is used to download gated local models) ---
    hf_token: str = ""
    hf_model_id: str = "Qwen/Qwen3-235B-A22B-Instruct-2507"
    hf_provider: str = "auto"
    hf_max_new_tokens: int = Field(600, ge=50, le=4000)
    hf_temperature: float = Field(0.3, ge=0.0, le=2.0)
    hf_timeout_seconds: float = Field(45.0, gt=0)

    # --- Request limits ---
    max_message_chars: int = Field(1500, ge=50, le=10000)
    max_history_messages: int = Field(8, ge=0, le=40)
    max_request_bytes: int = Field(262_144, ge=1024)
    rate_limit: str = "20/minute"

    # --- Safety engine ---
    emergency_number: str = "999"

    # --- CORS ---
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    @property
    def cors_origin_list(self) -> list[str]:
        origins = [o.strip().rstrip("/") for o in self.cors_origins.split(",") if o.strip()]
        if "*" in origins:
            raise ValueError("CORS_ORIGINS must list explicit origins; '*' is not allowed.")
        return origins

    @property
    def server_url(self) -> str:
        return self.server_base_url.rstrip("/")

    @property
    def hf_configured(self) -> bool:
        token = self.hf_token.strip()
        return bool(token) and not token.startswith("your_")


@lru_cache
def get_settings() -> Settings:
    """Cached settings instance (call get_settings.cache_clear() in tests)."""
    return Settings()
