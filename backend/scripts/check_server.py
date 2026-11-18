"""Check your local llama-server / Ollama model in English and Bangla.

Run from backend/ (venv active) AFTER starting the server:
    python -m scripts.check_server
"""
import asyncio
import time

from app.config import get_settings
from app.services import server_service
from app.services.huggingface_service import LLMServiceError

PROMPTS = {
    "English": ("In two sentences, what is dehydration?", "en"),
    "Bangla": ("ডিহাইড্রেশন কী? দুই বাক্যে বাংলায় বলুন।", "bn"),
}
HINTS = {
    "model_unavailable": "Is the server running? Check SERVER_BASE_URL, and SERVER_MODEL if you use Ollama.",
    "loading": "The server is still loading the model; wait and retry.",
    "timeout": "Too slow. Try a smaller quantization / context, GPU offload, or raise SERVER_TIMEOUT_SECONDS.",
    "bad_response": "The server answered with empty/unexpected output (thinking mode?). Try SERVER_DISABLE_THINKING=true.",
}


async def main() -> int:
    settings = get_settings()
    print(f"Server: {settings.server_url}  model: {settings.server_model}  state: {await server_service.check_ready()}")
    ok = True
    for label, (prompt, lang) in PROMPTS.items():
        start = time.time()
        try:
            text = await server_service.generate_reply(prompt, [], lang)
            print(f"[{label}] OK in {time.time() - start:.1f}s:\n{text}\n")
        except LLMServiceError as exc:
            ok = False
            print(f"[{label}] FAILED ({exc.code}). {HINTS.get(exc.code, '')}")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
