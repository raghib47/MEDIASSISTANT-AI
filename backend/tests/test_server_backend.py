"""Tests for the local OpenAI-compatible server backend (llama-server / Ollama), fully mocked."""
import httpx
import pytest

from app.config import get_settings
from app.services import server_service


@pytest.fixture
def server_backend(monkeypatch):
    monkeypatch.setenv("LLM_BACKEND", "server")
    monkeypatch.setenv("SERVER_BASE_URL", "http://fake-llm/v1")
    monkeypatch.setenv("SERVER_MODEL", "qwen3.5-9b")
    get_settings.cache_clear()
    yield
    monkeypatch.undo()
    get_settings.cache_clear()


def mock_server(monkeypatch, handler):
    monkeypatch.setattr(
        server_service, "_make_client",
        lambda timeout: httpx.AsyncClient(transport=httpx.MockTransport(handler), timeout=timeout),
    )


def ok_reply(text):
    return httpx.Response(200, json={"choices": [{"message": {"role": "assistant", "content": text}}]})


def test_success_sends_expected_payload_and_strips_think(client, server_backend, monkeypatch):
    seen = {}

    def handler(request):
        import json
        seen["url"] = str(request.url)
        seen["body"] = json.loads(request.content)
        return ok_reply("<think>reasoning</think>Dehydration means low body fluid.")

    mock_server(monkeypatch, handler)
    r = client.post("/chat", json={"message": "What is dehydration?"})
    assert r.status_code == 200 and r.json()["reply"] == "Dehydration means low body fluid."
    assert seen["url"] == "http://fake-llm/v1/chat/completions"
    body = seen["body"]
    assert body["model"] == "qwen3.5-9b"
    assert body["chat_template_kwargs"] == {"enable_thinking": False}
    assert body["messages"][0]["role"] == "system" and body["messages"][-1]["content"] == "What is dehydration?"
    assert body["max_tokens"] == 700


def test_thinking_flag_can_be_disabled_in_settings(client, server_backend, monkeypatch):
    monkeypatch.setenv("SERVER_DISABLE_THINKING", "false")
    get_settings.cache_clear()
    seen = {}

    def handler(request):
        import json
        seen["body"] = json.loads(request.content)
        return ok_reply("ok")

    mock_server(monkeypatch, handler)
    assert client.post("/chat", json={"message": "hi there"}).status_code == 200
    assert "chat_template_kwargs" not in seen["body"]


def test_bangla_question_uses_bangla_instruction(client, server_backend, monkeypatch):
    seen = {}

    def handler(request):
        import json
        seen["body"] = json.loads(request.content)
        return ok_reply("ডিহাইড্রেশন মানে শরীরে পানির ঘাটতি।")

    mock_server(monkeypatch, handler)
    r = client.post("/chat", json={"message": "ডিহাইড্রেশন কী?"})
    assert r.status_code == 200 and r.json()["language"] == "bn"
    assert "Bangla" in seen["body"]["messages"][0]["content"]


@pytest.mark.parametrize(
    "handler_result, expected_status",
    [
        (httpx.ConnectError("refused"), 503),          # server not running
        (httpx.ReadTimeout("slow"), 504),              # too slow
        (httpx.Response(401, text="no"), 502),         # bad key
        (httpx.Response(429, text="busy"), 429),
        (httpx.Response(404, text="model not found"), 503),
        (httpx.Response(500, text="boom"), 503),
        (httpx.Response(503, text="Loading model"), 503),
        (httpx.Response(200, text="not json"), 502),
        (httpx.Response(200, json={"choices": []}), 502),
        (httpx.Response(200, json={"choices": [{"message": {"content": "<think>only thoughts"}}]}), 502),
    ],
)
def test_server_failures_map_to_friendly_errors(client, server_backend, monkeypatch, handler_result, expected_status):
    def handler(request):
        if isinstance(handler_result, Exception):
            raise handler_result
        return handler_result

    mock_server(monkeypatch, handler)
    r = client.post("/chat", json={"message": "What is anemia?"})
    assert r.status_code == expected_status
    assert "boom" not in r.json()["detail"] and "fake-llm" not in r.json()["detail"]


def test_loading_message_when_server_is_starting(client, server_backend, monkeypatch):
    mock_server(monkeypatch, lambda request: httpx.Response(503, text="Loading model"))
    detail = client.post("/chat", json={"message": "What is anemia?"}).json()["detail"]
    assert "starting up" in detail


@pytest.mark.parametrize(
    "handler_result, expected",
    [(httpx.Response(200, json={"data": []}), "ready"), (httpx.Response(503, text="Loading model"), "loading"),
     (httpx.ConnectError("refused"), "failed"), (httpx.Response(500, text="x"), "failed")],
)
def test_health_reports_server_state(client, server_backend, monkeypatch, handler_result, expected):
    def handler(request):
        if isinstance(handler_result, Exception):
            raise handler_result
        return handler_result

    mock_server(monkeypatch, handler)
    body = client.get("/health").json()
    assert body["llm_backend"] == "server" and body["llm_state"] == expected
    assert body["llm_configured"] == (expected == "ready")


def test_emergency_still_works_when_server_is_down(client, server_backend, monkeypatch):
    def handler(request):
        raise httpx.ConnectError("refused")

    mock_server(monkeypatch, handler)
    r = client.post("/chat", json={"message": "He is unconscious"})
    assert r.status_code == 200 and r.json()["emergency"] is True
