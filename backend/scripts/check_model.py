"""Check which Hugging Face models actually work for YOUR token (English + Bangla).

Run from the backend/ folder (venv active):

    python -m scripts.check_model
    python -m scripts.check_model Qwen/Qwen2.5-72B-Instruct meta-llama/Llama-3.3-70B-Instruct

With no arguments it tests HF_MODEL_ID from .env plus a few fallback candidates.
Availability depends on your account, provider and current free-tier credits - this script
tells you the truth instead of guessing. It makes a few small requests (uses credits).
"""
import sys
import time

from app.config import get_settings
from app.services.huggingface_service import _get_client, classify_error, extract_text

FALLBACKS = ["Qwen/Qwen2.5-72B-Instruct", "meta-llama/Llama-3.3-70B-Instruct"]
PROMPTS = {
    "English": "In two sentences, what is dehydration?",
    "Bangla": "ডিহাইড্রেশন কী? দুই বাক্যে বাংলায় বলুন।",
}


def main() -> int:
    settings = get_settings()
    if not settings.hf_configured:
        print("HF_TOKEN is missing. Copy backend/.env.example to backend/.env and set it.")
        return 1

    models = sys.argv[1:] or [settings.hf_model_id, *[m for m in FALLBACKS if m != settings.hf_model_id]]
    client = _get_client(settings)
    working: list[str] = []

    for model in models:
        print(f"\n=== {model} (provider={settings.hf_provider}) ===")
        ok = True
        for label, prompt in PROMPTS.items():
            start = time.time()
            try:
                completion = client.chat.completions.create(
                    model=model,
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=120,
                    temperature=0.3,
                )
                text = extract_text(completion)
                print(f"[{label}] OK in {time.time() - start:.1f}s: {text[:160]!r}")
            except Exception as exc:  # noqa: BLE001
                ok = False
                print(f"[{label}] FAILED ({classify_error(exc)}): {type(exc).__name__}")
        if ok:
            working.append(model)

    print("\nWorking models:", working or "none")
    if working:
        print(f"Set HF_MODEL_ID={working[0]} in backend/.env (read the Bangla output yourself to judge quality).")
    return 0 if working else 2


if __name__ == "__main__":
    raise SystemExit(main())
