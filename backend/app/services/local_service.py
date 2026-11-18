"""Run a model locally with Hugging Face Transformers (default: google/medgemma-1.5-4b-it).

Why local: small gated models like MedGemma are usually not served by Inference Providers,
and local inference has no credits/quotas. Trade-offs: needs RAM/GPU, first start downloads
several GB, and CPU generation is slow.

Design notes
* The model loads in a background thread at server start, so the API (and the emergency
  safety engine) works immediately. Until it is ready, /chat returns a friendly "loading" error.
* One generation at a time (a lock), because one model instance is shared.
* Heavy imports (torch/transformers) happen inside load_model(), so tests and the remote
  backend don't need them installed.
"""
from __future__ import annotations

import asyncio
import contextlib
import logging
import re
import threading
from typing import Any

from app.config import Settings, get_settings
from app.services.huggingface_service import LLMServiceError, build_messages, classify_error

logger = logging.getLogger("mediassist.local")

_THINK_BLOCK = re.compile(r"<think>.*?</think>", re.DOTALL | re.IGNORECASE)

# status: idle -> loading -> ready | failed
_STATE: dict[str, Any] = {"status": "idle", "error": None, "model": None, "processor": None, "dtype": None}
_load_lock = threading.Lock()
_gen_lock = threading.Lock()


def state() -> str:
    """Coarse state for /health: ready | loading | failed."""
    status = _STATE["status"]
    return "loading" if status == "idle" else status


def _reset_for_tests() -> None:
    _STATE.update(status="idle", error=None, model=None, processor=None, dtype=None)


def _classify_load_error(exc: Exception) -> str:
    text = str(exc).lower()
    if isinstance(exc, ImportError):
        return "not_configured"  # torch / transformers not installed
    if "gated" in text or "401" in text or "403" in text or "access to model" in text or "unauthorized" in text:
        return "auth"  # license not accepted, or token missing/invalid
    if isinstance(exc, MemoryError) or "out of memory" in text or "not enough memory" in text:
        return "model_unavailable"
    code = classify_error(exc)
    return "model_unavailable" if code == "unknown" else code


def load_model(settings: Settings | None = None) -> None:
    """Download (first run) and load the model. Idempotent; raises LLMServiceError on failure."""
    settings = settings or get_settings()
    with _load_lock:
        if _STATE["status"] == "ready":
            return
        _STATE.update(status="loading", error=None)
        try:
            import torch
            from transformers import AutoModelForImageTextToText, AutoProcessor

            dtype = {"bfloat16": torch.bfloat16, "float16": torch.float16, "float32": torch.float32}[settings.local_dtype]
            token = settings.hf_token.strip() if settings.hf_configured else None  # needed for gated repos
            logger.info("Loading local model %s (dtype=%s). First run downloads several GB...", settings.local_model_id, settings.local_dtype)
            processor = AutoProcessor.from_pretrained(settings.local_model_id, token=token)
            model = AutoModelForImageTextToText.from_pretrained(
                settings.local_model_id, torch_dtype=dtype, device_map="auto", token=token
            )
            model.eval()
        except Exception as exc:  # noqa: BLE001
            code = _classify_load_error(exc)
            _STATE.update(status="failed", error=code)
            logger.error("Local model load failed: code=%s type=%s", code, type(exc).__name__)
            raise LLMServiceError(code) from exc
        _STATE.update(status="ready", model=model, processor=processor, dtype=dtype)
        logger.info("Local model ready on device=%s", getattr(model, "device", "?"))


def start_background_load(settings: Settings | None = None) -> None:
    """Start loading in a daemon thread (does not block server start or shutdown)."""

    def _run() -> None:
        try:
            load_model(settings)
        except LLMServiceError:
            pass  # already logged; state is "failed" and /chat reports it

    threading.Thread(target=_run, name="local-model-loader", daemon=True).start()


def _inference_mode():
    try:
        import torch

        return torch.inference_mode()
    except ImportError:  # tests without torch
        return contextlib.nullcontext()


def _generate_blocking(messages: list[dict[str, str]], settings: Settings) -> str:
    model, processor, dtype = _STATE["model"], _STATE["processor"], _STATE["dtype"]
    # MedGemma's processor expects content as a list of typed parts.
    chat = [{"role": m["role"], "content": [{"type": "text", "text": m["content"]}]} for m in messages]

    gen_kwargs: dict[str, Any] = {"max_new_tokens": settings.local_max_new_tokens}
    if settings.hf_temperature > 0:
        gen_kwargs.update(do_sample=True, temperature=settings.hf_temperature)
    else:
        gen_kwargs["do_sample"] = False

    with _gen_lock:  # one generation at a time
        inputs = processor.apply_chat_template(
            chat, add_generation_prompt=True, tokenize=True, return_dict=True, return_tensors="pt"
        )
        inputs = inputs.to(model.device, dtype=dtype)
        input_len = inputs["input_ids"].shape[-1]
        with _inference_mode():
            output = model.generate(**inputs, **gen_kwargs)
        text = processor.decode(output[0][input_len:], skip_special_tokens=True)

    text = _THINK_BLOCK.sub("", text).strip()
    if not text:
        raise LLMServiceError("bad_response")
    return text


async def generate_reply(user_message: str, history: list[dict[str, str]], language: str) -> str:
    settings = get_settings()
    status = _STATE["status"]
    if status == "idle":
        start_background_load(settings)
        raise LLMServiceError("loading")
    if status == "loading":
        raise LLMServiceError("loading")
    if status == "failed":
        raise LLMServiceError(_STATE["error"] or "model_unavailable")

    messages = build_messages(user_message, history, language, settings.max_history_messages)
    try:
        return await asyncio.wait_for(
            asyncio.to_thread(_generate_blocking, messages, settings), timeout=settings.local_timeout_seconds
        )
    except asyncio.TimeoutError as exc:
        # The worker thread keeps running until it finishes; later requests queue behind it.
        raise LLMServiceError("timeout") from exc
    except LLMServiceError:
        raise
    except Exception as exc:  # noqa: BLE001
        code = "model_unavailable" if "out of memory" in str(exc).lower() else "unknown"
        logger.warning("Local generation failed: code=%s type=%s", code, type(exc).__name__)
        raise LLMServiceError(code) from exc
