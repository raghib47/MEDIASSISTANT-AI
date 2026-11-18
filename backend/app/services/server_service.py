"""Talk to a local OpenAI-compatible server (llama.cpp `llama-server`, Ollama, LM Studio...).

Typical use: run a quantized GGUF such as Qwen3.5-9B Q4_K_M with llama-server, then point
SERVER_BASE_URL at it. No torch/transformers needed in this project.
"""
from __future__ import annotations

import logging
import re
from typing import Any

import httpx

from app.config import get_settings
from app.services.huggingface_service import LLMServiceError, build_messages

logger = logging.getLogger("mediassist.server")

# Also drops an unclosed <think> (e.g. generation cut off mid-thought).
_THINK_BLOCK = re.compile(r"<think>.*?(?:</think>|$)", re.DOTALL | re.IGNORECASE)


def _make_client(timeout: float) -> httpx.AsyncClient:
    """Factory kept separate so tests can inject a fake transport."""
    return httpx.AsyncClient(timeout=timeout)


def _headers() -> dict[str, str]:
    key = get_settings().server_api_key.strip()
    return {"Authorization": f"Bearer {key}"} if key else {}


async def check_ready() -> str:
    """For /health: ready | loading | failed (server unreachable)."""
    settings = get_settings()
    try:
        async with _make_client(2.0) as client:
            resp = await client.get(f"{settings.server_url}/models", headers=_headers())
    except httpx.HTTPError:
        return "failed"
    if resp.status_code == 200:
        return "ready"
    if resp.status_code == 503:
        return "loading"  # llama-server answers 503 while the model is still loading
    return "failed"


def _code_for_status(status: int, body: str) -> str:
    if status in (401, 403):
        return "auth"
    if status == 429:
        return "rate_limit"
    if status == 503 and "loading" in body.lower():
        return "loading"
    return "model_unavailable"  # 404 (wrong model name), 5xx, etc.


def _extract_text(data: Any) -> str:
    try:
        content = data["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as exc:
        raise LLMServiceError("bad_response") from exc
    if not isinstance(content, str):
        raise LLMServiceError("bad_response")
    text = _THINK_BLOCK.sub("", content).strip()
    if not text:
        raise LLMServiceError("bad_response")
    return text


async def generate_reply(user_message: str, history: list[dict[str, str]], language: str) -> str:
    settings = get_settings()
    payload: dict[str, Any] = {
        "model": settings.server_model,
        "messages": build_messages(user_message, history, language, settings.max_history_messages),
        "max_tokens": settings.server_max_new_tokens,
        "temperature": settings.hf_temperature,
        "stream": False,
    }
    if settings.server_disable_thinking:
        # Qwen3.x "thinking" mode is slow and emits reasoning text; turn it off per request.
        payload["chat_template_kwargs"] = {"enable_thinking": False}

    try:
        async with _make_client(settings.server_timeout_seconds) as client:
            resp = await client.post(f"{settings.server_url}/chat/completions", json=payload, headers=_headers())
    except httpx.TimeoutException as exc:
        raise LLMServiceError("timeout") from exc
    except httpx.HTTPError as exc:  # connection refused, DNS, etc. -> server not running
        logger.warning("Local server unreachable: type=%s", type(exc).__name__)
        raise LLMServiceError("model_unavailable") from exc

    if resp.status_code >= 400:
        code = _code_for_status(resp.status_code, resp.text[:300])
        logger.warning("Local server error: status=%s code=%s", resp.status_code, code)
        raise LLMServiceError(code)
    try:
        data = resp.json()
    except ValueError as exc:
        raise LLMServiceError("bad_response") from exc
    return _extract_text(data)
