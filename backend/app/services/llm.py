"""Dispatcher: send the request to the configured backend."""
from app.config import get_settings
from app.services import huggingface_service, local_service, server_service


async def llm_state() -> str:
    """ready | loading | failed | not_configured (for /health)."""
    settings = get_settings()
    if settings.llm_backend == "server":
        return await server_service.check_ready()
    if settings.llm_backend == "local":
        return local_service.state()
    return "ready" if settings.hf_configured else "not_configured"


async def generate_reply(user_message: str, history: list[dict[str, str]], language: str) -> str:
    backend = get_settings().llm_backend
    if backend == "server":
        return await server_service.generate_reply(user_message, history, language)
    if backend == "local":
        return await local_service.generate_reply(user_message, history, language)
    return await huggingface_service.generate_reply(user_message, history, language)
