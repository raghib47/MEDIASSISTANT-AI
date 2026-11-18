"""FastAPI application entrypoint.

Run from the backend/ folder:  uvicorn app.main:app --reload --port 8000
"""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi.errors import RateLimitExceeded

from app.config import get_settings
from app.limiter import limiter
from app.messages import INVALID_REQUEST_DETAIL, PAYLOAD_TOO_LARGE_DETAIL, RATE_LIMIT_DETAIL
from app.routes.chat import router as chat_router
from app.services import local_service
from app.services.llm import llm_state

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

VERSION = "0.1.0"
settings = get_settings()


@asynccontextmanager
async def lifespan(_app: FastAPI):
    # Load the local model in a background thread so the API (and the emergency safety
    # engine) is available immediately, even while the model is still downloading/loading.
    if get_settings().llm_backend == "local":
        local_service.start_background_load()
    yield


app = FastAPI(
    lifespan=lifespan,
    title="MediAssist AI API",
    version=VERSION,
    description=(
        "Bilingual (English/Bangla) general healthcare information chatbot. "
        "**Not a doctor. Not for diagnosis or emergencies.** Prototype for a hackathon."
    ),
)

# ---- Rate limiting -----------------------------------------------------------------
app.state.limiter = limiter


@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request: Request, exc: RateLimitExceeded) -> JSONResponse:
    return JSONResponse(
        status_code=429, content={"detail": RATE_LIMIT_DETAIL}, headers={"Retry-After": "30"}
    )


# ---- Friendly validation errors (don't leak internal field details) -----------------
@app.exception_handler(RequestValidationError)
async def validation_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    return JSONResponse(status_code=422, content={"detail": INVALID_REQUEST_DETAIL})


# ---- Request-size limit (checks Content-Length; pydantic limits are the real guard) ----
@app.middleware("http")
async def limit_request_size(request: Request, call_next):
    length = request.headers.get("content-length")
    if length and length.isdigit() and int(length) > settings.max_request_bytes:
        return JSONResponse(status_code=413, content={"detail": PAYLOAD_TOO_LARGE_DETAIL})
    return await call_next(request)


# ---- CORS: only the configured origins. Added LAST so it is the outermost middleware ----
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type"],
)

app.include_router(chat_router)


@app.get("/", tags=["meta"], summary="API welcome message")
async def root() -> dict[str, str]:
    return {
        "name": "MediAssist AI API",
        "message": "Welcome to MediAssist AI. This is a prototype; it is not a doctor.",
        "docs": "/docs",
        "version": VERSION,
    }


@app.get("/health", tags=["meta"], summary="Backend health check")
async def health() -> dict[str, object]:
    # Report only coarse state, never tokens or other internals.
    state = await llm_state()  # "ready" | "loading" | "failed" | "not_configured"
    return {
        "status": "ok",
        "version": VERSION,
        "llm_backend": get_settings().llm_backend,
        "llm_state": state,
        "llm_configured": state == "ready",
    }
