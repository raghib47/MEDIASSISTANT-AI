"""User-facing error messages in English and Bangla.

Internal details (tokens, stack traces, upstream bodies) are never put in these messages.
"""
from typing import Literal

Lang = Literal["en", "bn"]

# code -> (HTTP status, {lang: message})
LLM_ERRORS: dict[str, tuple[int, dict[str, str]]] = {
    "not_configured": (
        503,
        {
            "en": "The AI service isn't set up on the server yet. Please contact the administrator.",
            "bn": "সার্ভারে এআই সেবা এখনো সেটআপ করা হয়নি। অনুগ্রহ করে প্রশাসকের সাথে যোগাযোগ করুন।",
        },
    ),
    "auth": (
        502,
        {
            "en": "The AI service couldn't be reached because of a server configuration problem. Please try again later.",
            "bn": "সার্ভারের কনফিগারেশন সমস্যার কারণে এআই সেবার সাথে সংযোগ করা যায়নি। অনুগ্রহ করে পরে আবার চেষ্টা করুন।",
        },
    ),
    "rate_limit": (
        429,
        {
            "en": "The AI service is receiving too many requests right now. Please wait a minute and try again.",
            "bn": "এই মুহূর্তে এআই সেবায় অনেক বেশি অনুরোধ আসছে। অনুগ্রহ করে এক মিনিট অপেক্ষা করে আবার চেষ্টা করুন।",
        },
    ),
    "quota_exceeded": (
        429,
        {
            "en": "The free AI usage allowance has been used up for now. Please try again later.",
            "bn": "বিনামূল্যের এআই ব্যবহারের সীমা আপাতত শেষ হয়ে গেছে। অনুগ্রহ করে পরে আবার চেষ্টা করুন।",
        },
    ),
    "model_unavailable": (
        503,
        {
            "en": "The AI model is temporarily unavailable. Please try again in a little while.",
            "bn": "এআই মডেলটি সাময়িকভাবে পাওয়া যাচ্ছে না। কিছুক্ষণ পরে আবার চেষ্টা করুন।",
        },
    ),
    "loading": (
        503,
        {
            "en": "The AI model is still starting up (the first start can take several minutes). Please try again shortly.",
            "bn": "এআই মডেলটি এখনো চালু হচ্ছে (প্রথমবার কয়েক মিনিট লাগতে পারে)। অনুগ্রহ করে একটু পরে আবার চেষ্টা করুন।",
        },
    ),
    "timeout": (
        504,
        {
            "en": "The AI service took too long to respond. Please try again.",
            "bn": "এআই সেবার উত্তর দিতে অনেক সময় লাগছে। অনুগ্রহ করে আবার চেষ্টা করুন।",
        },
    ),
    "bad_response": (
        502,
        {
            "en": "The AI service returned an unexpected response. Please try again.",
            "bn": "এআই সেবা থেকে অপ্রত্যাশিত উত্তর এসেছে। অনুগ্রহ করে আবার চেষ্টা করুন।",
        },
    ),
    "unknown": (
        502,
        {
            "en": "Something went wrong while generating a response. Please try again.",
            "bn": "উত্তর তৈরি করার সময় কিছু একটা সমস্যা হয়েছে। অনুগ্রহ করে আবার চেষ্টা করুন।",
        },
    ),
}


def llm_error(code: str, lang: Lang) -> tuple[int, str]:
    """Return (http_status, localized_message) for an LLM error code."""
    status, texts = LLM_ERRORS.get(code, LLM_ERRORS["unknown"])
    return status, texts[lang]


# Generic errors where the user's language isn't known yet -> bilingual text.
RATE_LIMIT_DETAIL = (
    "Too many requests. Please wait a moment and try again. / "
    "অনেক বেশি অনুরোধ হয়েছে। কিছুক্ষণ অপেক্ষা করে আবার চেষ্টা করুন।"
)
INVALID_REQUEST_DETAIL = (
    "Invalid request. Please enter a message (not empty, within the length limit). / "
    "অনুরোধটি সঠিক নয়। অনুগ্রহ করে একটি বার্তা লিখুন (ফাঁকা নয় এবং সীমার মধ্যে)।"
)
PAYLOAD_TOO_LARGE_DETAIL = (
    "Request is too large. / অনুরোধটি অনেক বড়।"
)
