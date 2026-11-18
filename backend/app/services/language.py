"""Lightweight language detection for English vs Bangla (no external model needed)."""
import re
from typing import Literal

Lang = Literal["en", "bn"]

# Bengali Unicode block: U+0980 - U+09FF
_BANGLA = re.compile(r"[\u0980-\u09FF]")
_LATIN = re.compile(r"[A-Za-z]")


def detect_language(text: str) -> Lang:
    """Return "bn" if Bangla script makes up a meaningful share of the letters, else "en".

    Limitation: romanized Bangla ("Banglish", e.g. "amar jor hoyeche") is detected as English.
    """
    bangla = len(_BANGLA.findall(text))
    latin = len(_LATIN.findall(text))
    if bangla == 0:
        return "en"
    return "bn" if bangla / (bangla + latin) >= 0.4 else "en"
