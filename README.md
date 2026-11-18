# MediAssist AI: Bilingual (English / বাংলা) Healthcare Information Chatbot

An AI Engineering Hackathon prototype. MediAssist AI explains **general** health information, common symptoms and
medical terms in English or Bangla. It is **not a doctor**: it never diagnoses, never prescribes, and routes
emergency warning signs to urgent care through a separate deterministic safety engine.

> ⚠️ **Prototype only.** Not clinically validated, not a medical device, not for real patients, and no privacy-law
> compliance (HIPAA, GDPR, etc.) is claimed or assessed. Use no real patient data.

## Features
- Bilingual chat: auto language detection, replies in the user's language, Bangla Unicode + font support
- Conversation context (last 8 messages), validated and trimmed server-side; one-click "New chat"
- **Deterministic emergency detection** (English + Bangla, negation-aware), answered instantly **without calling the LLM**
- Safe system prompt: not a doctor, no diagnosis, no personal dosing, no invented facts, advises professional care
- Friendly bilingual errors for timeouts, rate limits, auth problems, unavailable models, bad responses
- Security: backend-only token, input validation, request-size limit, strict CORS, per-IP rate limiting, no message logging or storage
- 112 automated backend tests (pytest)

## Architecture
```
React (Vite) :5173 ──fetch──▶ FastAPI :8000 ──▶ Safety engine (regex rules, EN+BN)
                                   │               └─ emergency? → fixed reply returned immediately (no LLM)
                                   └──▶ Hugging Face Inference Providers (chat completion, model from .env)
```

## Tech stack
React 18 + Vite (JSX/CSS, Fetch API) · Python, FastAPI, Pydantic v2, Uvicorn · `huggingface_hub` `InferenceClient`
(Inference Providers) · slowapi (rate limiting) · pytest. No Streamlit/n8n/Gemini/OpenAI/Next.js.

## Folder structure
```
MediAssist-AI/
├── backend/
│   ├── app/
│   │   ├── main.py              # app, CORS, middleware, /, /health
│   │   ├── config.py            # settings from .env
│   │   ├── limiter.py           # rate limiting
│   │   ├── messages.py          # bilingual error text
│   │   ├── routes/chat.py       # POST /chat
│   │   ├── schemas/chat.py      # Pydantic models
│   │   ├── services/huggingface_service.py  # LLM call, system prompt, error mapping
│   │   ├── services/language.py # EN/BN detection
│   │   └── safety_engine/rules.py  # emergency rules (prototype)
│   ├── scripts/check_model.py   # test which HF models work for your token
│   ├── tests/                   # pytest suite
│   ├── .env.example · requirements.txt · pytest.ini
├── frontend/
│   ├── src/components/ (Navbar, ChatWindow, ChatMessage, ChatInput, TypingIndicator, EmergencyAlert)
│   ├── src/services/api.js · src/utils/ · src/styles/main.css · App.jsx · main.jsx
│   └── .env.example · package.json · vite.config.js · index.html
├── .gitignore
└── README.md
```

## Installation
Requirements: Python 3.10+, Node 18+, a free Hugging Face account.

### 1. Hugging Face token
Create a token at <https://huggingface.co/settings/tokens> (fine-grained, with permission to call Inference Providers).
The token lives **only** in `backend/.env`; never put it in the frontend.

### 2. Backend
```bash
cd backend
python -m venv .venv
source .venv/bin/activate            # Windows PowerShell: .venv\Scripts\Activate.ps1
pip install -r requirements.txt
cp .env.example .env                 # Windows: copy .env.example .env  → then edit HF_TOKEN
python -m scripts.check_model        # verify a model works for YOUR token (English + Bangla)
uvicorn app.main:app --reload --port 8000
```
Open <http://localhost:8000/docs> (Swagger UI).

### 3. Frontend
```bash
cd frontend
npm install
cp .env.example .env                 # Windows: copy .env.example .env
npm run dev                          # http://localhost:5173
```

## Running Qwen3.5-9B (Q4 GGUF) locally: the default setup
The backend talks to a local **llama.cpp `llama-server`** (OpenAI-compatible API), so no torch/transformers is needed.

1. Install llama.cpp: `winget install llama.cpp` (Windows) · `brew install llama.cpp` (macOS) · or a release binary from GitHub.
2. Start the model (the first run downloads about 6 GB):
   ```
   llama-server -hf bartowski/Qwen_Qwen3.5-9B-GGUF:Q4_K_M --jinja -c 4096 --port 8080
   ```
   Add `-ngl 99` if you have a GPU with enough VRAM. Any other Qwen3.5-9B Q4_K_M GGUF repo works too.
3. In `backend/.env` (already the default in `.env.example`):
   ```
   LLM_BACKEND=server
   SERVER_BASE_URL=http://127.0.0.1:8080/v1
   SERVER_MODEL=qwen3.5-9b
   SERVER_DISABLE_THINKING=true
   ```
4. Check English + Bangla quality: `python -m scripts.check_server`, then start the backend.

Notes: Ollama also works (`SERVER_BASE_URL=http://127.0.0.1:11434/v1`, `SERVER_MODEL=<your ollama tag>`), but its handling of
the thinking switch is unverified, so `<think>` blocks are also stripped defensively. Other engines: `LLM_BACKEND=local`
(Transformers, e.g. MedGemma, see `requirements-local.txt`) and `LLM_BACKEND=huggingface` (remote, needs credits).
CPU-only generation can take a minute or more per reply; the frontend waits up to `VITE_REQUEST_TIMEOUT_MS`.

## Hugging Face remote model configuration (LLM_BACKEND=huggingface)
Edit `backend/.env`, no code changes needed:
```
HF_MODEL_ID=Qwen/Qwen3-235B-A22B-Instruct-2507   # candidate default; verify with check_model
HF_PROVIDER=auto                                  # or a specific provider name
```
- Free-tier access is limited (small monthly credits), and which models work depends on your account/provider.
  Run `python -m scripts.check_model [model ids…]` to test candidates and **read the Bangla output yourself**.
- Fallback candidates: `Qwen/Qwen2.5-72B-Instruct`, `meta-llama/Llama-3.3-70B-Instruct` (Bangla quality may be weaker).
- If the model emits `<think>…</think>` reasoning blocks, they are stripped automatically.

## API
| Method | Path | Description |
|---|---|---|
| GET | `/` | Welcome message |
| GET | `/health` | `{status, version, llm_configured}` |
| POST | `/chat` | Body: `{"message": "...", "history": [{"role":"user"\|"assistant","content":"..."}]}` |

`POST /chat` → `{reply, language: "en"\|"bn", emergency: bool, source: "safety_engine"\|"llm", emergency_signs: []}`

Errors always return `{"detail": "<friendly message>"}`: `413` too large · `422` invalid · `429` rate-limited (this API or
provider/credits) · `502` provider error · `503` model unavailable / not configured · `504` timeout.

## Testing
```bash
cd backend && pytest -q
```
| # | Scenario | How it's covered |
|---|---|---|
| 1 | English question | `test_english_question` |
| 2 | Bangla question | `test_bangla_question` |
| 3 | Follow-up conversation | `test_follow_up_passes_history`, history-trimming tests |
| 4 | Empty message | `test_invalid_requests_return_422` |
| 5 | Invalid request | same + non-JSON, oversized (413) |
| 6 | Hugging Face failure | `test_hugging_face_failures_map_to_friendly_errors` |
| 7 | Rate limit | provider 429/402 mapping + `test_api_rate_limit` |
| 8 | Emergency (English) | `test_emergency_english_skips_llm` |
| 9 | Emergency (Bangla) | `test_emergency_bangla_skips_llm` |
| 10 | Negated keyword | `test_negated_*` in `test_safety_engine.py` |
| 11 | Backend unavailable | **Manual:** stop uvicorn, send a message → error banner + "Backend offline" badge; upstream-down covered by tests |
| 12 | Frontend ↔ backend | **Manual:** run both, then follow the checklist below |

**Manual integration checklist:** (a) status badge shows *Online*; (b) ask "What is dehydration?" → English answer;
(c) ask "ডিহাইড্রেশন কী?" → Bangla answer; (d) ask a follow-up ("what causes it?") → answer uses context;
(e) type "I have severe chest pain" → red emergency bubble, banner and call button, instant reply;
(f) type "I have no chest pain" → normal answer; (g) "New chat" resets everything.

**Swagger UI:** open `/docs` → `POST /chat` → *Try it out* → paste `{"message":"What is anemia?","history":[]}` → *Execute*.
Try an emergency message and an empty one (`422`).

## Known limitations
- The safety rules are **keyword/regex based, unvalidated by clinicians**, and will miss some emergencies and over-flag others
  (negation/context handling is heuristic). Romanized Bangla ("Banglish") is not understood by the rules or the language detector.
- Only the *current* message is scanned for emergencies, not earlier turns.
- LLM output can be wrong; the system prompt reduces but cannot eliminate this. No output moderation or fact-checking layer.
- Free-tier credits/rate limits can cause errors during demos; Bangla quality depends on the model you choose.
- Rate limiting is in-memory and per-process; the request-size check relies on `Content-Length`.
- The emergency number defaults to Bangladesh's 999: change `EMERGENCY_NUMBER` / `VITE_EMERGENCY_NUMBER` for other countries.
- No accounts, no persistence (by design): refreshing the page clears the conversation.

## Future improvements
Clinician review and a validated test set for the safety rules · scan recent history, not just the last message ·
Banglish support · streaming responses · retrieval from vetted sources (e.g., WHO/MoHFW) with citations · output moderation ·
Redis-backed rate limiting · Docker + deployment · accessibility audit and voice input.
