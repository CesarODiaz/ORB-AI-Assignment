"""Pull obvious facts from a user turn. The model fills whatever this misses."""

import re

from orb_agent.textutil import fold

_EMAIL = re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}")
_REFERENCE = re.compile(r"\bORB[-\s]?(\d{3,6})\b", re.IGNORECASE)
_PHONE = re.compile(
    r"(?:\+34|0034)?[\s.\-]*[6-9]\d{2}[\s.\-]*\d{3}[\s.\-]*\d{3}\b"
)
_PHONE_INTL = re.compile(r"\+\d{1,3}(?:[\s.\-]?\d){8,14}")
_NAME = re.compile(
    r"\b(?:me llamo|mi nombre es|soy|my name is|i am|i'm)\s+([a-zA-ZÀ-ÿ' .\-]{2,40})",
    re.IGNORECASE,
)
_NAME_STOP = re.compile(
    r"\b(y|e|and|mi|my|el|la|los|las|un|una|del|de|pedido|order|correo|"
    r"email|telefono|phone|porque|porque|que|con|se)\b",
    re.IGNORECASE,
)
_NAME_BLOCK = {
    "de", "del", "un", "una", "el", "la", "cliente", "yo", "the", "from",
    "a", "very", "just", "not", "no",
}

_ITEMS = (
    ("lamp", ("lampara", "aplique", "flexo", "lamp", "lighting", "chandelier")),
    ("furniture", ("mueble", "silla", "mesa", "aparador", "chair", "table", "cabinet", "furniture")),
    ("textile", ("tapiz", "tapizado", "tela", "upholstery", "cushion", "cojin")),
)
_CATEGORIES = (
    ("electrical", ("chispa", "chisporrote", "enchufe", "cable", "cableado", "electri", "spark", "socket", "wiring", "quem")),
    ("billing", ("factura", "cobro", "reembolso", "invoice", "billing", "refund", "payment")),
    ("scheduling", ("cita", "cuando podeis", "reagendar", "appointment", "reschedule", "drop off")),
    ("parts", ("falta una pieza", "falta el", "tornillo", "missing part", "spare part")),
    ("finish", ("barniz", "acabado", "mancha", "color", "varnish", "stain", "finish")),
    ("damage", ("roto", "rota", "rompi", "rajad", "pata", "broken", "crack", "snapped")),
)
_URGENCY = (
    ("critical", ("chispa", "chispas", "humo", "quemad", "spark", "sparks", "smoke", "fire", "peligro")),
    ("high", ("urgente", "esta semana", "cuanto antes", "asap", "this week", "urgent")),
    ("low", ("sin prisa", "cuando podais", "no rush", "whenever", "no hurry")),
    ("medium", ("pronto", "soon", "esta quincena")),
)
_WINDOWS = (
    ("morning", ("por la manana", "mananas", "in the morning", "morning")),
    ("afternoon", ("por la tarde", "tardes", "in the afternoon", "afternoon")),
    ("evening", ("por la noche", "noches", "in the evening", "evening")),
)


def _phrase_hit(folded: str, phrases: tuple[str, ...]) -> bool:
    return any(phrase in folded for phrase in phrases)


def _last_match(folded: str, table: tuple) -> str | None:
    """The last mention wins, so a correction beats the word it replaces."""
    best = None
    best_at = -1
    for label, phrases in table:
        for phrase in phrases:
            at = folded.rfind(phrase)
            if at > best_at:
                best = label
                best_at = at
    return best


def _name_from(text: str) -> str | None:
    match = _NAME.search(text)
    if not match:
        return None
    raw = _NAME_STOP.split(match.group(1), maxsplit=1)[0]
    parts = [part for part in raw.replace(",", " ").split() if part]
    if not parts or fold(parts[0]) in _NAME_BLOCK:
        return None
    kept = []
    for part in parts:
        if fold(part) in _NAME_BLOCK:
            break
        kept.append(part)
        if len(kept) == 3:
            break
    if not kept:
        return None
    return " ".join(kept)


def _looks_like_problem(text: str, folded: str) -> bool:
    stripped = _EMAIL.sub(" ", text)
    stripped = _PHONE.sub(" ", stripped)
    stripped = _PHONE_INTL.sub(" ", stripped)
    stripped = _REFERENCE.sub(" ", stripped)
    compact = " ".join(stripped.split())
    if len(compact) < 20:
        return False
    if fold(compact) in {"si", "no", "ok", "vale", "gracias", "yes", "thanks", "hello", "hola"}:
        return False
    problem = _last_match(folded, _CATEGORIES) is not None or _last_match(folded, _ITEMS) is not None
    return problem or len(compact) >= 50


def extract_fields(text: str) -> dict:
    folded = fold(text)
    found: dict = {}

    email = _EMAIL.search(text)
    if email:
        found["contact_email"] = email.group(0)

    reference = _REFERENCE.search(text)
    if reference:
        found["reference_code"] = f"ORB-{reference.group(1)}"

    phone_source = _EMAIL.sub(" ", text)
    phone_source = _REFERENCE.sub(" ", phone_source)
    phone = _PHONE.search(phone_source) or _PHONE_INTL.search(phone_source)
    if phone:
        found["contact_phone"] = phone.group(0)

    name = _name_from(text)
    if name:
        found["customer_name"] = name

    item = _last_match(folded, _ITEMS)
    if item:
        found["item_type"] = item
    if _phrase_hit(folded, ("chispa", "chisporrote", "spark", "humo", "quemad", "olor a quemado")):
        found["category"] = "electrical"
    else:
        category = _last_match(folded, _CATEGORIES)
        if category:
            found["category"] = category
    if _phrase_hit(folded, ("chispa", "chispas", "humo", "quemad", "spark", "sparks", "smoke", "fire", "peligro")):
        found["urgency"] = "critical"
    else:
        urgency = _last_match(folded, _URGENCY[1:])
        if urgency:
            found["urgency"] = urgency
    window = _last_match(folded, _WINDOWS)
    if window:
        found["preferred_contact"] = window

    if _looks_like_problem(text, folded):
        found["description"] = " ".join(text.split())
    return found
