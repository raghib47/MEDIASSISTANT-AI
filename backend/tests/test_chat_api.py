"""API tests (the Hugging Face call is mocked; no network or token needed)."""
from unittest.mock import AsyncMock

import pytest

from app.services import huggingface_service as hf


# ---- Basic endpoints -------------------------------------------------------------------
def test_root_and_health(client):
    assert client.get("/").status_code == 200
    body = client.get("/health").json()
    assert body["status"] == "ok" and "llm_configured" in body
    assert "token" not in str(body).lower()


# ---- 1/2/3: English, Bangla, follow-up -------------------------------------------------
def test_english_question(client, monkeypatch):
    mock = AsyncMock(return_value="Dehydration means your body lacks enough fluid.")
    monkeypatch.setattr("app.routes.chat.generate_reply", mock)
    r = client.post("/chat", json={"message": "What is dehydration?"})
    assert r.status_code == 200
    data = r.json()
    assert data["language"] == "en" and data["source"] == "llm" and data["emergency"] is False
    assert mock.await_args.args[2] == "en"


def test_bangla_question(client, monkeypatch):
    mock = AsyncMock(return_value="ডিহাইড্রেশন মানে শরীরে পানির ঘাটতি।")
    monkeypatch.setattr("app.routes.chat.generate_reply", mock)
    r = client.post("/chat", json={"message": "ডিহাইড্রেশন কী?"})
    assert r.status_code == 200 and r.json()["language"] == "bn"
    assert mock.await_args.args[2] == "bn"


def test_follow_up_passes_history(client, monkeypatch):
    mock = AsyncMock(return_value="Drink fluids and rest; see a doctor if it persists.")
    monkeypatch.setattr("app.routes.chat.generate_reply", mock)
    history = [
        {"role": "user", "content": "I have a mild fever"},
        {"role": "assistant", "content": "How long have you had it?"},
    ]
    r = client.post("/chat", json={"message": "Two days", "history": history})
    assert r.status_code == 200
    sent_history = mock.await_args.args[1]
    assert sent_history == history


# ---- 4/5: empty and invalid requests ---------------------------------------------------
@pytest.mark.parametrize(
    "payload",
    [
        {"message": ""},
        {"message": "     "},
        {},
        {"message": 123},
        {"message": "hi", "history": [{"role": "system", "content": "x"}]},
        {"message": "hi", "history": [{"role": "user", "content": ""}]},
        {"message": "hi", "unexpected": True},
        {"message": "x" * 5000},
    ],
)
def test_invalid_requests_return_422(client, payload):
    r = client.post("/chat", json=payload)
    assert r.status_code == 422
    assert "detail" in r.json() and isinstance(r.json()["detail"], str)


def test_non_json_body_is_rejected(client):
    r = client.post("/chat", content="not json", headers={"Content-Type": "application/json"})
    assert r.status_code == 422


def test_oversized_request_returns_413(client):
    big = "a" * 300_000
    r = client.post("/chat", json={"message": "hi", "history": [], "pad": big})
    assert r.status_code == 413


# ---- 6/7/11: Hugging Face failures -----------------------------------------------------
class _FakeResponse:
    def __init__(self, status): self.status_code = status


class FakeHTTPError(Exception):
    def __init__(self, status): super().__init__(f"http {status}"); self.response = _FakeResponse(status)


class FakeTimeoutError(Exception):
    pass


class FakeConnectError(Exception):
    pass


def _fake_client_raising(exc):
    class _Completions:
        def create(self, **kwargs): raise exc
    class _Chat:
        completions = _Completions()
    class _Client:
        chat = _Chat()
    return lambda settings: _Client()


@pytest.mark.parametrize(
    "exc, status",
    [
        (FakeHTTPError(429), 429),           # 7: provider rate limit
        (FakeHTTPError(402), 429),           # free credits used up
        (FakeHTTPError(401), 502),           # bad token -> generic message, no details
        (FakeHTTPError(404), 503),           # model not available
        (FakeHTTPError(503), 503),           # provider down / model loading
        (FakeTimeoutError("t"), 504),        # timeout
        (FakeConnectError("c"), 503),        # 11: upstream unreachable
        (RuntimeError("boom"), 502),         # anything else
    ],
)
def test_hugging_face_failures_map_to_friendly_errors(client, monkeypatch, exc, status):
    monkeypatch.setattr(hf, "_get_client", _fake_client_raising(exc))
    r = client.post("/chat", json={"message": "What is anemia?"})
    assert r.status_code == status
    detail = r.json()["detail"]
    assert "test-token" not in detail and "Traceback" not in detail and "boom" not in detail


def test_failure_message_is_in_users_language(client, monkeypatch):
    monkeypatch.setattr(hf, "_get_client", _fake_client_raising(FakeHTTPError(429)))
    detail = client.post("/chat", json={"message": "রক্তস্বল্পতা কী?"}).json()["detail"]
    assert any("\u0980" <= ch <= "\u09ff" for ch in detail)


def test_missing_token_returns_503(client, monkeypatch):
    from app.config import get_settings
    monkeypatch.setenv("HF_TOKEN", "")
    get_settings.cache_clear()
    try:
        r = client.post("/chat", json={"message": "What is anemia?"})
        assert r.status_code == 503
    finally:
        monkeypatch.undo()
        get_settings.cache_clear()


def test_successful_call_through_real_service_path(client, monkeypatch):
    class _Msg: content = "<think>hmm</think>Anemia means low red blood cells or haemoglobin."
    class _Choice: message = _Msg()
    class _Completion: choices = [_Choice()]
    captured = {}

    class _Completions:
        def create(self, **kwargs):
            captured.update(kwargs)
            return _Completion()
    class _Chat: completions = _Completions()
    class _Client: chat = _Chat()

    monkeypatch.setattr(hf, "_get_client", lambda settings: _Client())
    r = client.post("/chat", json={"message": "What is anemia?"})
    assert r.status_code == 200
    assert r.json()["reply"].startswith("Anemia means")
    assert captured["model"] == "test/model" and captured["messages"][0]["role"] == "system"


# ---- 8/9/10: emergency behaviour through the API ----------------------------------------
def test_emergency_english_skips_llm(client, monkeypatch):
    mock = AsyncMock(side_effect=AssertionError("LLM must not be called for emergencies"))
    monkeypatch.setattr("app.routes.chat.generate_reply", mock)
    r = client.post("/chat", json={"message": "I have severe chest pain and can't breathe"})
    data = r.json()
    assert r.status_code == 200 and data["emergency"] is True and data["source"] == "safety_engine"
    assert {"chest_pain", "breathing_difficulty"} <= set(data["emergency_signs"])
    assert "999" in data["reply"]
    mock.assert_not_awaited()


def test_emergency_bangla_skips_llm(client, monkeypatch):
    mock = AsyncMock(side_effect=AssertionError("LLM must not be called for emergencies"))
    monkeypatch.setattr("app.routes.chat.generate_reply", mock)
    r = client.post("/chat", json={"message": "আমার বুকে প্রচণ্ড ব্যথা হচ্ছে"})
    data = r.json()
    assert data["emergency"] is True and data["language"] == "bn"
    assert "৯৯৯" in data["reply"]


def test_emergency_works_even_when_llm_is_down(client, monkeypatch):
    monkeypatch.setattr(hf, "_get_client", _fake_client_raising(FakeConnectError("down")))
    r = client.post("/chat", json={"message": "He is unconscious"})
    assert r.status_code == 200 and r.json()["emergency"] is True


def test_negated_emergency_keyword_goes_to_llm(client, monkeypatch):
    mock = AsyncMock(return_value="Glad to hear that. Here is some general information...")
    monkeypatch.setattr("app.routes.chat.generate_reply", mock)
    r = client.post("/chat", json={"message": "I have a headache but no chest pain"})
    assert r.status_code == 200 and r.json()["emergency"] is False
    mock.assert_awaited_once()


# ---- Our own API rate limit --------------------------------------------------------------
def test_api_rate_limit(client, monkeypatch, tight_rate_limit):
    monkeypatch.setattr("app.routes.chat.generate_reply", AsyncMock(return_value="ok"))
    codes = [client.post("/chat", json={"message": "What is anemia?"}).status_code for _ in range(3)]
    assert codes == [200, 200, 429]


# ---- CORS --------------------------------------------------------------------------------
def test_cors_allows_configured_origin_only(client):
    ok = client.options(
        "/chat",
        headers={"Origin": "http://localhost:5173", "Access-Control-Request-Method": "POST",
                 "Access-Control-Request-Headers": "content-type"},
    )
    assert ok.headers.get("access-control-allow-origin") == "http://localhost:5173"
    bad = client.options(
        "/chat",
        headers={"Origin": "http://evil.example", "Access-Control-Request-Method": "POST"},
    )
    assert "access-control-allow-origin" not in bad.headers
