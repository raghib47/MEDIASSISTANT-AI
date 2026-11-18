"""Per-IP rate limiting (slowapi, in-memory).

In-memory counters reset on restart and are per-process; for production behind a proxy or
multiple workers, use a shared store (e.g. Redis) and configure trusted proxy headers.
"""
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.config import get_settings

limiter = Limiter(key_func=get_remote_address)


def rate_limit_value(*_args, **_kwargs) -> str:
    """Dynamic limit string so it can be changed via .env (and in tests)."""
    return get_settings().rate_limit
