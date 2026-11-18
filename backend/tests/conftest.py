"""Test setup. Environment is set BEFORE the app is imported so no real token/limits are used."""
import os

os.environ["LLM_BACKEND"] = "huggingface"
os.environ["HF_TOKEN"] = "test-token-not-real"
os.environ["HF_MODEL_ID"] = "test/model"
os.environ["RATE_LIMIT"] = "1000/minute"
os.environ["EMERGENCY_NUMBER"] = "999"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.config import get_settings  # noqa: E402
from app.limiter import limiter  # noqa: E402
from app.main import app  # noqa: E402


@pytest.fixture
def client() -> TestClient:
    limiter.reset()
    return TestClient(app)


@pytest.fixture
def tight_rate_limit(monkeypatch):
    """Lower the per-IP limit to 2/minute for one test, then restore it."""
    monkeypatch.setenv("RATE_LIMIT", "2/minute")
    get_settings.cache_clear()
    limiter.reset()
    yield
    monkeypatch.undo()
    get_settings.cache_clear()
    limiter.reset()
