"""POST /chat - the main chatbot endpoint."""
import logging

from fastapi import APIRouter, HTTPException, Request

from app.config import get_settings
from app.limiter import limiter, rate_limit_value
from app.messages import llm_error
from app.safety_engine.rules import build_emergency_response, check_emergency
from app.schemas.chat import ChatRequest, ChatResponse, ErrorResponse
from app.services.huggingface_service import LLMServiceError
from app.services.llm import generate_reply
from app.services.language import detect_language

logger = logging.getLogger("mediassist.chat")
router = APIRouter(tags=["chat"])


@router.post(
    "/chat",
    response_model=ChatResponse,
    responses={
        413: {"model": ErrorResponse, "description": "Request too large"},
        422: {"model": ErrorResponse, "description": "Invalid request"},
        429: {"model": ErrorResponse, "description": "Rate limited (this API or the AI provider)"},
        502: {"model": ErrorResponse, "description": "AI provider error"},
        503: {"model": ErrorResponse, "description": "AI model unavailable / not configured"},
        504: {"model": ErrorResponse, "description": "AI provider timeout"},
    },
    summary="Send a message and get a bilingual healthcare answer",
)
@limiter.limit(rate_limit_value)
async def chat(request: Request, payload: ChatRequest) -> ChatResponse:
    settings = get_settings()
    language = detect_language(payload.message)

    # 1) Deterministic safety check FIRST. If it fires, the LLM is never called,
    #    so urgent advice is instant and cannot be delayed by (or depend on) a model.
    safety = check_emergency(payload.message)
    if safety.is_emergency:
        return ChatResponse(
            reply=build_emergency_response(safety, language, settings.emergency_number),
            language=language,
            emergency=True,
            source="safety_engine",
            emergency_signs=list(safety.rule_ids),
        )

    # 2) Otherwise ask the Hugging Face model.
    history = [m.model_dump() for m in payload.history]
    try:
        reply = await generate_reply(payload.message, history, language)
    except LLMServiceError as exc:
        status, detail = llm_error(exc.code, language)
        headers = {"Retry-After": "30"} if status == 429 else None
        raise HTTPException(status_code=status, detail=detail, headers=headers) from exc

    return ChatResponse(reply=reply, language=language, emergency=False, source="llm")
