"""Tests for language detection and prompt/history construction."""
from app.services.huggingface_service import build_messages, extract_text, sanitize_history, LLMServiceError
from app.services.language import detect_language
import pytest


def test_detect_language():
    assert detect_language("What is diabetes?") == "en"
    assert detect_language("ডায়াবেটিস কী?") == "bn"
    assert detect_language("আমার fever হয়েছে") == "bn"
    assert detect_language("12345 ???") == "en"


def test_history_is_trimmed_and_alternates():
    history = []
    for i in range(10):
        history.append({"role": "user", "content": f"q{i}"})
        history.append({"role": "assistant", "content": f"a{i}"})
    cleaned = sanitize_history(history, 8)
    assert len(cleaned) <= 8
    assert cleaned[0]["role"] == "user"
    assert cleaned[-1]["role"] == "assistant"
    assert all(a["role"] != b["role"] for a, b in zip(cleaned, cleaned[1:]))


def test_history_drops_leading_assistant_and_merges_duplicates():
    history = [
        {"role": "assistant", "content": "hello"},
        {"role": "user", "content": "a"},
        {"role": "user", "content": "b"},
        {"role": "assistant", "content": "c"},
    ]
    cleaned = sanitize_history(history, 8)
    assert cleaned == [{"role": "user", "content": "a\n\nb"}, {"role": "assistant", "content": "c"}]


def test_build_messages_shape_and_language_instruction():
    msgs = build_messages("ডায়াবেটিস কী?", [], "bn", 8)
    assert msgs[0]["role"] == "system" and "Bangla" in msgs[0]["content"]
    assert msgs[-1] == {"role": "user", "content": "ডায়াবেটিস কী?"}
    assert "not a doctor" in msgs[0]["content"].lower()


class _Msg:
    def __init__(self, content): self.content = content
class _Choice:
    def __init__(self, content): self.message = _Msg(content)
class _Completion:
    def __init__(self, content): self.choices = [_Choice(content)]


def test_extract_text_strips_think_blocks():
    assert extract_text(_Completion("<think>secret</think>Hello")) == "Hello"


@pytest.mark.parametrize("bad", [_Completion(""), _Completion("<think>x</think>"), object()])
def test_extract_text_rejects_unusable(bad):
    with pytest.raises(LLMServiceError) as exc:
        extract_text(bad)
    assert exc.value.code == "bad_response"
