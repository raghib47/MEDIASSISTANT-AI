# 🩺 MediAssist AI
### Bilingual (English / বাংলা) Healthcare Information Chatbot

MediAssist AI is an AI-powered bilingual healthcare information chatbot developed as an **AI Engineering Hackathon prototype**. It provides general health information, explains common symptoms and medical terminology, and answers healthcare-related questions in both English and Bangla.

The application uses a **locally hosted Qwen3.5-9B (Q4_K_M GGUF) language model** through `llama.cpp`, allowing AI inference to run on the user's own computer instead of relying on a cloud-based LLM API.

It also includes a separate deterministic safety engine that detects potential emergency warning signs and returns immediate emergency guidance without calling the language model.

> ⚠️ **Important Disclaimer:** MediAssist AI is an educational prototype only. It is not clinically validated, is not a medical device, and is not intended for real patient care. It does not diagnose diseases or prescribe medication. No HIPAA, GDPR, or other privacy-law compliance is claimed or assessed. Never use real patient data with this prototype.

---

## ✨ Features

### 🌐 1. Bilingual AI Chatbot
- Supports English and Bangla (বাংলা).
- Automatically detects the user's language.
- Responds in the same language as the user's question.
- Supports Bangla Unicode text and font rendering.
- Explains general healthcare information and medical terminology.

### 🤖 2. Locally Hosted AI Model
- Uses Qwen3.5-9B (Q4_K_M GGUF).
- Runs locally through `llama.cpp`.
- Uses the OpenAI-compatible local API exposed by `llama-server`.
- Does not require the Hugging Face Inference API or OpenAI API.
- Keeps model inference on the user's computer.

### 🛡️ 3. Emergency Safety Detection
- Separate deterministic, rule-based safety engine.
- Detects potential emergency warning signs in English and Bangla.
- Uses regex-based keyword matching and heuristic negation handling.
- Returns predefined emergency guidance immediately.
- Skips the LLM call when an emergency rule is triggered.
- Includes an emergency alert interface and emergency call button.

### 💬 4. Conversation Management
- Maintains conversation context using the last 8 messages.
- Validates and trims conversation history on the backend.
- Supports follow-up questions.
- Includes a one-click **New Chat** option to reset the conversation.

### 🔒 5. Security and Privacy-Conscious Design
- No cloud LLM inference API is required.
- No model API token is exposed in the frontend.
- Backend input validation using Pydantic.
- Request-size limits.
- Strict CORS configuration.
- Per-IP rate limiting.
- No conversation message logging or storage by the application.

### ⚡ 6. Error Handling
- Friendly bilingual error messages.
- Handles backend connection failures.
- Handles model timeouts.
- Handles rate-limit errors.
- Handles unavailable models and invalid responses.
- Provides frontend status indicators.

### 🧪 7. Automated Testing
- 112 automated backend tests using pytest.
- Tests for English and Bangla conversations.
- Emergency detection tests.
- Negation handling tests.
- API validation and rate-limiting tests.
- LLM error-handling tests.

---

## 🏗️ System Architecture

MediAssist AI uses a locally hosted LLM architecture.

```text
                 USER
                   |
                   v
        React + Vite Frontend
              :5173
                   |
              HTTP Fetch
                   |
                   v
          FastAPI Backend
               :8000
                   |
          +--------+---------+
          |                  |
          v                  v
    Safety Engine       LLM Service
    (English/Bangla)         |
          |                  |
          |                  v
          |             llama-server
          |                :8080
          |                  |
          |                  v
          |           Qwen3.5-9B
          |             Q4_K_M
          |             GGUF
          |                  |
          |                  v
          |            Local Inference
          |                  |
          +--------+---------+
                   |
                   v
             Chat Response
                   |
                   v
            React Frontend
```

### How it works

1. The user sends a message through the React frontend.
2. The frontend sends the message and conversation history to the FastAPI backend.
3. The backend validates the incoming request.
4. The safety engine checks the current message for potential emergency warning signs.
5. If an emergency is detected, a predefined safety response is returned immediately without calling the LLM.
6. Otherwise, the backend forwards the conversation to the locally running Qwen3.5-9B model through the `llama-server` API.
7. The model generates a response.
8. The backend returns the response to the frontend.
9. The frontend displays the answer in English or Bangla.

---

## 🛠️ Technology Stack

| Category | Technology |
|---|---|
| Frontend | React 18 |
| Build Tool | Vite |
| Programming Language | JavaScript |
| Styling | CSS |
| Backend | Python |
| Backend Framework | FastAPI |
| Data Validation | Pydantic v2 |
| ASGI Server | Uvicorn |
| AI Model | Qwen3.5-9B |
| Model Format | GGUF |
| Quantization | Q4_K_M |
| Local Inference | llama.cpp |
| API Communication | OpenAI-compatible local API |
| Rate Limiting | slowapi |
| Testing | pytest |

**AI inference:** The language model runs locally on the machine hosting `llama-server`. The project does not use Hugging Face Inference Providers, Gemini API, OpenAI API, or another cloud-based LLM inference service.

---

## 📂 Project Structure

```text
MediAssist-AI/
│
├── backend/
│   │
│   ├── app/
│   │   ├── main.py
│   │   │
│   │   ├── config.py
│   │   │
│   │   ├── limiter.py
│   │   │
│   │   ├── messages.py
│   │   │
│   │   ├── routes/
│   │   │   └── chat.py
│   │   │
│   │   ├── schemas/
│   │   │   └── chat.py
│   │   │
│   │   ├── services/
│   │   │   └── LLM integration service
│   │   │
│   │   ├── safety_engine/
│   │   │   └── rules.py
│   │
│   ├── scripts/
│   │   └── check_server.py
│   │
│   ├── tests/
│   │
│   ├── .env.example
│   ├── requirements.txt
│   └── pytest.ini
│
├── frontend/
│   │
│   ├── src/
│   │   ├── components/
│   │   │   ├── Navbar.jsx
│   │   │   ├── ChatWindow.jsx
│   │   │   ├── ChatMessage.jsx
│   │   │   ├── ChatInput.jsx
│   │   │   ├── TypingIndicator.jsx
│   │   │   └── EmergencyAlert.jsx
│   │   │
│   │   ├── services/
│   │   │   └── api.js
│   │   │
│   │   ├── utils/
│   │   │
│   │   ├── styles/
│   │   │   └── main.css
│   │   │
│   │   ├── App.jsx
│   │   └── main.jsx
│   │
│   ├── .env.example
│   ├── package.json
│   ├── vite.config.js
│   └── index.html
│
├── .gitignore
└── README.md
```

---

## 💻 Installation and Setup

### Prerequisites

Make sure you have installed:

- Python 3.10 or higher
- Node.js 18 or higher
- npm
- llama.cpp
- Sufficient RAM or GPU VRAM to run the selected model
- Git

### Step 1: Clone the Repository

```bash
git clone https://github.com/YOUR_USERNAME/MediAssist-AI.git

cd MediAssist-AI
```

Replace `YOUR_USERNAME` with your GitHub username.

### Step 2: Install and Configure llama.cpp

MediAssist AI uses `llama-server` to run the local Qwen3.5-9B model.

**Windows (using winget):**

```powershell
winget install llama.cpp
```

**macOS (using Homebrew):**

```bash
brew install llama.cpp
```

For other operating systems, use the official llama.cpp repository:

https://github.com/ggml-org/llama.cpp

### Step 3: Download and Run the Qwen3.5-9B Model

The default model configuration uses:

- Model: Qwen3.5-9B
- Format: GGUF
- Quantization: Q4_K_M

Start the local model server:

```bash
llama-server -hf bartowski/Qwen_Qwen3.5-9B-GGUF:Q4_K_M --jinja -c 4096 --port 8080
```

The first run downloads approximately 6 GB of model files. Actual download size may vary.

If you have a compatible GPU with sufficient VRAM, you can use:

```bash
llama-server -hf bartowski/Qwen_Qwen3.5-9B-GGUF:Q4_K_M --jinja -c 4096 --port 8080 -ngl 99
```

**Note:** The `-hf` option downloads model weights from a Hugging Face model repository. This does NOT use the Hugging Face Inference API. All model inference happens locally through llama.cpp. No Hugging Face API token is required for the standard public model download.

Keep the model server running while using MediAssist AI.

### Step 4: Configure the Backend

Open a new terminal:

```bash
cd backend
```

Create a Python virtual environment:

```bash
python -m venv .venv
```

Activate the environment.

**Windows PowerShell:**

```powershell
.venv\Scripts\Activate.ps1
```

**macOS / Linux:**

```bash
source .venv/bin/activate
```

Install the dependencies:

```bash
pip install -r requirements.txt
```

Create the environment configuration file:

**Windows:**

```powershell
copy .env.example .env
```

**macOS / Linux:**

```bash
cp .env.example .env
```

Configure your backend `.env` file:

```env
LLM_BACKEND=server

SERVER_BASE_URL=http://127.0.0.1:8080/v1

SERVER_MODEL=qwen3.5-9b

SERVER_DISABLE_THINKING=true
```

These settings connect FastAPI to your locally running llama.cpp server.

### Step 5: Verify the Local Model

Run the model connection and response checks:

```bash
python -m scripts.check_server
```

This script checks whether the local model is responding and tests English and Bangla output.

Make sure `llama-server` is running before executing the script.

### Step 6: Start the FastAPI Backend

Run:

```bash
uvicorn app.main:app --reload --port 8000
```

The backend will be available at:

```text
http://localhost:8000
```

Open the interactive API documentation:

```text
http://localhost:8000/docs
```

### Step 7: Start the React Frontend

Open another terminal:

```bash
cd frontend
```

Install frontend dependencies:

```bash
npm install
```

Create the frontend environment file:

**Windows:**

```powershell
copy .env.example .env
```

**macOS / Linux:**

```bash
cp .env.example .env
```

Start the development server:

```bash
npm run dev
```

Open the application:

```text
http://localhost:5173
```

---

## 🔄 Running the Application

For the complete application to work, three services need to be running.

| Service | Command | Port |
|---|---|---|
| llama.cpp Model Server | `llama-server ...` | 8080 |
| FastAPI Backend | `uvicorn app.main:app --reload --port 8000` | 8000 |
| React Frontend | `npm run dev` | 5173 |

**Recommended startup order:**

1. Start the llama.cpp model server.
2. Start the FastAPI backend.
3. Start the React frontend.
4. Open `http://localhost:5173`.

---

## 🔌 API Documentation

MediAssist AI provides a REST API through FastAPI.

### Available Endpoints

| Method | Endpoint | Description |
|---|---|---|
| GET | `/` | Welcome message |
| GET | `/health` | Backend health and configuration status |
| POST | `/chat` | Send a message to the chatbot |

### POST `/chat`

**Request Body:**

```json
{
  "message": "What is anemia?",
  "history": []
}
```

**Example with conversation history:**

```json
{
  "message": "What causes it?",
  "history": [
    {
      "role": "user",
      "content": "What is anemia?"
    },
    {
      "role": "assistant",
      "content": "Anemia is a condition involving a reduced number of healthy red blood cells or insufficient hemoglobin."
    }
  ]
}
```

**Successful Response:**

```json
{
  "reply": "Anemia is a condition in which the blood has insufficient healthy red blood cells or hemoglobin.",
  "language": "en",
  "emergency": false,
  "source": "llm",
  "emergency_signs": []
}
```

**Emergency Response:**

```json
{
  "reply": "Your symptoms may indicate a medical emergency. Please seek urgent medical attention immediately.",
  "language": "en",
  "emergency": true,
  "source": "safety_engine",
  "emergency_signs": []
}
```

The emergency response is generated by the deterministic safety engine and does not require an LLM call.

### Response Fields

| Field | Description |
|---|---|
| `reply` | Chatbot response |
| `language` | Detected language (`en` or `bn`) |
| `emergency` | Whether an emergency rule was triggered |
| `source` | Response source (`llm` or `safety_engine`) |
| `emergency_signs` | Detected emergency warning signs |

### Error Handling

The API returns friendly error messages using the following HTTP status codes:

| Status Code | Description |
|---|---|
| 413 | Request payload too large |
| 422 | Invalid request |
| 429 | Rate limit exceeded |
| 502 | Local model server or upstream response error |
| 503 | Model unavailable or not configured |
| 504 | Request timeout |

---

## 🛡️ Emergency Safety Engine

One of the important features of MediAssist AI is its separate emergency detection system.

Unlike the language model, the safety engine uses predefined rules to identify potential emergency warning signs.

### How it works

1. Receives the user's current message.
2. Checks for predefined emergency-related patterns.
3. Applies heuristic negation handling.
4. Determines whether an emergency rule has been triggered.
5. Returns a predefined emergency response immediately.
6. Skips the language model for triggered emergency messages.

### Supported Languages

- English
- Bangla (বাংলা)

### Example Messages

| User Message | Expected Behavior |
|---|---|
| I have severe chest pain | Emergency detection |
| I am having difficulty breathing | Emergency detection |
| আমার বুকে প্রচণ্ড ব্যথা হচ্ছে | Emergency detection |
| আমার শ্বাস নিতে খুব কষ্ট হচ্ছে | Emergency detection |
| I have no chest pain | Normal chatbot response |

**Important:** This safety engine is experimental. It uses keyword and regex-based rules, not a clinically validated medical decision system. It can miss emergencies or incorrectly flag messages. A message that does not trigger an alert should never be interpreted as proof that a situation is safe.

---

## 🧪 Testing

The backend includes 112 automated tests written using pytest.

To run the tests:

```bash
cd backend

pytest -q
```

### Test Coverage

| No. | Test Scenario | Test Coverage |
|---|---|---|
| 1 | English question | `test_english_question` |
| 2 | Bangla question | `test_bangla_question` |
| 3 | Follow-up conversation | `test_follow_up_passes_history` |
| 4 | Empty message | `test_invalid_requests_return_422` |
| 5 | Invalid request | Validation and oversized request tests |
| 6 | Model failure | Friendly error handling tests |
| 7 | Rate limiting | `test_api_rate_limit` |
| 8 | English emergency | `test_emergency_english_skips_llm` |
| 9 | Bangla emergency | `test_emergency_bangla_skips_llm` |
| 10 | Negated keywords | `test_negated_*` |
| 11 | Backend unavailable | Manual integration test |
| 12 | Frontend-backend integration | Manual integration test |

### Manual Integration Testing

After starting all three services, verify the following:

- [ ] Frontend status badge displays Online.
- [ ] Ask "What is dehydration?" and verify an English response.
- [ ] Ask "ডিহাইড্রেশন কী?" and verify a Bangla response.
- [ ] Ask a follow-up question and verify conversation context.
- [ ] Enter "I have severe chest pain" and verify the emergency alert.
- [ ] Verify that emergency messages bypass the LLM.
- [ ] Enter "I have no chest pain" and verify normal response handling.
- [ ] Click New Chat and verify conversation reset.
- [ ] Stop the backend and verify the frontend displays an appropriate error.
- [ ] Stop llama-server and verify the backend handles the unavailable model.

### Testing Through Swagger UI

1. Start the FastAPI backend.
2. Open `http://localhost:8000/docs`.
3. Find `POST /chat`.
4. Click **Try it out**.
5. Enter:

```json
{
  "message": "What is anemia?",
  "history": []
}
```

6. Click **Execute**.

You can also test Bangla messages, emergency detection, and invalid requests.

---

## ⚙️ Model Configuration

The default model is:

| Parameter | Configuration |
|---|---|
| Model | Qwen3.5-9B |
| Model Repository | bartowski/Qwen_Qwen3.5-9B-GGUF |
| Quantization | Q4_K_M |
| Model Format | GGUF |
| Inference Engine | llama.cpp |
| Server | llama-server |
| Context Length | 4096 |
| Local API Port | 8080 |
| Thinking Mode | Disabled |

### Hardware Considerations

Performance depends on your computer's hardware.

- CPU-only inference is supported but may be slower.
- GPU acceleration can improve generation speed when supported.
- RAM and VRAM requirements depend on model configuration and runtime settings.
- The Q4_K_M quantized model requires approximately 6 GB of model storage, with additional memory needed for inference and context.

For lower-resource systems, consider using a smaller compatible GGUF model and adjusting the context length.

---

## ⚠️ Known Limitations

1. **Experimental emergency detection:** Safety rules are keyword/regex-based and have not been clinically validated.
2. **Negation handling:** Negation and context detection are heuristic and may produce false positives or false negatives.
3. **Banglish support:** Romanized Bangla is not currently supported by the safety rules or language detector.
4. **Current-message scanning:** Only the current message is checked for emergency warning signs, not earlier conversation turns.
5. **LLM hallucinations:** The model may generate inaccurate or misleading health information.
6. **No clinical validation:** Responses have not been reviewed or validated by medical professionals.
7. **Local hardware dependency:** Model performance depends on the user's CPU, RAM, GPU, and available VRAM.
8. **Response latency:** CPU-only generation may take a minute or longer for some responses.
9. **No persistent conversations:** Chat history is not stored by the application. Refreshing the page clears the conversation.
10. **In-memory rate limiting:** Rate limits are per-process and are not shared across multiple backend instances.
11. **Request-size validation:** The request-size check relies on the `Content-Length` header.
12. **Emergency number:** The default emergency number is Bangladesh's 999. Change `EMERGENCY_NUMBER` and `VITE_EMERGENCY_NUMBER` when configuring the application for another country.

---

## 🚀 Future Improvements

Some planned improvements include:

- Clinician review and validation of emergency detection rules.
- Improved emergency detection using more contextual analysis.
- Support for Banglish (Romanized Bangla).
- Conversation-history emergency scanning.
- Streaming AI responses.
- Retrieval-Augmented Generation (RAG) using trusted healthcare sources such as WHO and relevant national health authorities.
- Medical information citations and references.
- Additional output moderation and factual verification.
- Redis-backed rate limiting.
- Docker-based deployment.
- Accessibility improvements.
- Voice input and speech responses.
- Support for additional local language models.

---

## 👨‍💻 Project Purpose

MediAssist AI was developed as an AI Engineering Hackathon prototype to explore the practical application of locally hosted Large Language Models in bilingual healthcare information systems.

The project combines:

- Local LLM inference.
- Natural language processing.
- Bilingual conversational AI.
- Backend API development.
- Frontend development.
- Rule-based safety engineering.
- Automated software testing.

The main objective is to demonstrate how locally running AI models can be integrated into a conversational application while keeping cloud-based LLM inference out of the architecture.

---

## 📜 Disclaimer

MediAssist AI is an experimental educational project.

- It is not a doctor or a substitute for medical professionals.
- It does not diagnose medical conditions.
- It does not prescribe medications or personal dosages.
- Its emergency detection system is not clinically validated.
- Its AI-generated responses may contain errors.
- It is not intended for real patient care.
- No regulatory approval or privacy-law compliance is claimed.

For medical concerns, consult a qualified healthcare professional. For suspected emergencies, contact local emergency services immediately.

---

## ⭐ Acknowledgements

- [Qwen](https://github.com/QwenLM/Qwen3.5) – Language model.
- [llama.cpp](https://github.com/ggml-org/llama.cpp) – Local LLM inference engine.
- [React](https://react.dev/) – Frontend library.
- [Vite](https://vite.dev/) – Frontend development and build tool.
- [FastAPI](https://fastapi.tiangolo.com/) – Backend framework.
- [Pydantic](https://docs.pydantic.dev/) – Data validation.
- [pytest](https://docs.pytest.org/) – Automated testing.

---

**Developed as an AI Engineering Hackathon Project.**

If you find this project interesting, consider giving the repository a ⭐ on GitHub!
