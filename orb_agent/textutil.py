"""Small text helpers shared by extraction, retrieval, and flow control."""

import re
import unicodedata

_TOKEN = re.compile(r"[a-z0-9]{2,}", re.IGNORECASE)


def fold(text: str) -> str:
    """Lowercase and strip accents so Spanish and English match reliably."""
    normalized = unicodedata.normalize("NFD", text.strip().lower())
    return "".join(ch for ch in normalized if unicodedata.category(ch) != "Mn")


def tokens(text: str) -> set[str]:
    return set(_TOKEN.findall(fold(text)))


def clip(text: str, limit: int) -> str:
    cleaned = " ".join(text.split())
    if len(cleaned) <= limit:
        return cleaned
    return cleaned[: limit - 1].rstrip() + "…"
