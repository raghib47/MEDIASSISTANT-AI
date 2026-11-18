"""Tests for the Transformers backend using fakes (no torch/model needed)."""
import pytest

from app.services import local_service
from app.services.huggingface_service import LLMServiceError


class FakeIds:
    shape = (1, 5)


class FakeInputs(dict):
    def to(self, device, dtype=None):
        return self


class FakeProcessor:
    def __init__(self, text="Hello <b>"):
        self.text, self.chat = text, None

    def apply_chat_template(self, chat, **kwargs):
        self.chat = chat
        return FakeInputs(input_ids=FakeIds())

    def decode(self, tokens, skip_special_tokens):
        assert list(tokens) == [6, 7, 8]  # only newly generated tokens are decoded
        return self.text


class FakeModel:
    device = "cpu"

    def generate(self, **kwargs):
        self.kwargs = kwargs
        return [[1, 2, 3, 4, 5, 6, 7, 8]]


@pytest.fixture
def ready_local():
    local_service._reset_for_tests()
    proc, model = FakeProcessor(), FakeModel()
    local_service._STATE.update(status="ready", model=model, processor=proc, dtype=None)
    yield proc, model
    local_service._reset_for_tests()


def test_generate_blocking_formats_messages_and_returns_new_text(ready_local):
    from app.config import get_settings
    proc, model = ready_local
    out = local_service._generate_blocking(
        [{"role": "system", "content": "sys"}, {"role": "user", "content": "hi"}], get_settings()
    )
    assert out == "Hello <b>"
    assert proc.chat[1] == {"role": "user", "content": [{"type": "text", "text": "hi"}]}
    assert model.kwargs["max_new_tokens"] == 350 and model.kwargs["do_sample"] is True


def test_empty_generation_is_bad_response(ready_local):
    from app.config import get_settings
    ready_local[0].text = "<think>x</think>"
    with pytest.raises(LLMServiceError) as exc:
        local_service._generate_blocking([{"role": "user", "content": "hi"}], get_settings())
    assert exc.value.code == "bad_response"


def test_state_machine_errors(monkeypatch):
    import asyncio
    local_service._reset_for_tests()
    started = []
    monkeypatch.setattr(local_service, "start_background_load", lambda settings=None: started.append(1))
    with pytest.raises(LLMServiceError) as exc:
        asyncio.run(local_service.generate_reply("hi", [], "en"))
    assert exc.value.code == "loading" and started

    local_service._STATE.update(status="failed", error="auth")
    with pytest.raises(LLMServiceError) as exc:
        asyncio.run(local_service.generate_reply("hi", [], "en"))
    assert exc.value.code == "auth"
    local_service._reset_for_tests()


@pytest.mark.parametrize(
    "exc, code",
    [
        (ImportError("no torch"), "not_configured"),
        (OSError("You are trying to access a gated repo."), "auth"),
        (RuntimeError("CUDA out of memory"), "model_unavailable"),
    ],
)
def test_load_error_classification(exc, code):
    assert local_service._classify_load_error(exc) == code
