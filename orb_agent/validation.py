"""Normalize and validate intake fields. Invalid values are refused, not stored."""

import re

from orb_agent.config import CATEGORIES, CONTACT_WINDOWS, ITEM_TYPES, URGENCIES
from orb_agent.textutil import fold

_EMAIL = re.compile(r"^[a-z0-9._%+\-]+@[a-z0-9.\-]+\.[a-z]{2,}$")
_REFERENCE = re.compile(r"^ORB-\d{3,6}$")
_NAME_ALLOWED = re.compile(r"^[a-zA-ZÀ-ÿ][a-zA-ZÀ-ÿ' .\-]{1,58}[a-zA-ZÀ-ÿ.]$")

_ITEM_ALIASES = {
    "lamp": "lamp",
    "lampara": "lamp",
    "lighting": "lamp",
    "light": "lamp",
    "aplique": "lamp",
    "flexo": "lamp",
    "furniture": "furniture",
    "mueble": "furniture",
    "silla": "furniture",
    "mesa": "furniture",
    "chair": "furniture",
    "table": "furniture",
    "textile": "textile",
    "tapizado": "textile",
    "tela": "textile",
    "upholstery": "textile",
    "fabric": "textile",
    "other": "other",
    "otro": "other",
    "otra": "other",
}
_CATEGORY_ALIASES = {
    "damage": "damage",
    "dano": "damage",
    "rotura": "damage",
    "roto": "damage",
    "rota": "damage",
    "broken": "damage",
    "crack": "damage",
    "finish": "finish",
    "acabado": "finish",
    "barniz": "finish",
    "varnish": "finish",
    "stain": "finish",
    "electrical": "electrical",
    "electrico": "electrical",
    "electric": "electrical",
    "wiring": "electrical",
    "parts": "parts",
    "part": "parts",
    "pieza": "parts",
    "piezas": "parts",
    "missing": "parts",
    "scheduling": "scheduling",
    "cita": "scheduling",
    "horario": "scheduling",
    "appointment": "scheduling",
    "schedule": "scheduling",
    "billing": "billing",
    "factura": "billing",
    "cobro": "billing",
    "invoice": "billing",
    "payment": "billing",
    "other": "other",
    "otro": "other",
    "otra": "other",
}
_URGENCY_ALIASES = {
    "low": "low",
    "baja": "low",
    "bajo": "low",
    "medium": "medium",
    "media": "medium",
    "medio": "medium",
    "normal": "medium",
    "high": "high",
    "alta": "high",
    "alto": "high",
    "urgente": "high",
    "urgent": "high",
    "critical": "critical",
    "critica": "critical",
    "critico": "critical",
    "emergency": "critical",
}
_WINDOW_ALIASES = {
    "morning": "morning",
    "manana": "morning",
    "afternoon": "afternoon",
    "tarde": "afternoon",
    "evening": "evening",
    "noche": "evening",
    "any": "any",
    "cualquiera": "any",
    "indiferente": "any",
}


def empty_intake() -> dict:
    return {
        "customer_name": None,
        "contact_email": None,
        "contact_phone": None,
        "reference_code": None,
        "item_type": None,
        "category": None,
        "description": None,
        "urgency": None,
        "preferred_contact": None,
    }


def _clean(value) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text or fold(text) in {"null", "none", "n/a", "na", "unknown", "desconocido"}:
        return None
    return text


def normalize_field(key: str, value) -> tuple[bool, str | None, str | None]:
    """Return (ok, normalized, error_code). Unknown keys are ignored by the caller."""
    text = _clean(value)
    if text is None:
        return False, None, "empty"
    folded = fold(text)

    if key == "customer_name":
        compact = " ".join(text.split())
        if any(ch.isdigit() for ch in compact) or "@" in compact:
            return False, None, "invalid_name"
        if not _NAME_ALLOWED.match(compact):
            return False, None, "invalid_name"
        return True, " ".join(part.capitalize() for part in compact.split()), None

    if key == "contact_email":
        email = text.lower().strip(".,;")
        if not _EMAIL.match(email):
            return False, None, "invalid_email"
        return True, email, None

    if key == "contact_phone":
        digits = re.sub(r"\D", "", text)
        if digits.startswith("0034"):
            digits = digits[4:]
        elif digits.startswith("34") and len(digits) > 9:
            digits = digits[2:]
        if not digits.isdigit() or not 9 <= len(digits) <= 15:
            return False, None, "invalid_phone"
        return True, digits, None

    if key == "reference_code":
        code = folded.upper().replace(" ", "")
        code = code.replace("ORB", "ORB")
        if re.fullmatch(r"\d{3,6}", code):
            code = f"ORB-{code}"
        if not code.startswith("ORB-") and "ORB-" in code:
            code = code[code.index("ORB-"):]
        if not _REFERENCE.match(code):
            return False, None, "invalid_reference"
        return True, code, None

    if key == "item_type":
        mapped = _ITEM_ALIASES.get(folded)
        if mapped not in ITEM_TYPES:
            return False, None, "invalid_item"
        return True, mapped, None

    if key == "category":
        mapped = _CATEGORY_ALIASES.get(folded)
        if mapped not in CATEGORIES:
            return False, None, "invalid_category"
        return True, mapped, None

    if key == "urgency":
        mapped = _URGENCY_ALIASES.get(folded)
        if mapped not in URGENCIES:
            return False, None, "invalid_urgency"
        return True, mapped, None

    if key == "preferred_contact":
        mapped = _WINDOW_ALIASES.get(folded)
        if mapped not in CONTACT_WINDOWS:
            return False, None, "invalid_window"
        return True, mapped, None

    if key == "description":
        compact = " ".join(text.split())
        if len(compact) < 12:
            return False, None, "description_too_short"
        return True, compact[:600], None

    return False, None, "unknown_field"


def missing_fields(intake: dict) -> list[str]:
    missing = []
    if not intake.get("customer_name"):
        missing.append("customer_name")
    if not intake.get("contact_email") and not intake.get("contact_phone"):
        missing.append("contact")
    for key in ("item_type", "category", "description", "urgency"):
        if not intake.get(key):
            missing.append(key)
    return missing


def apply_fields(intake: dict, candidate: dict | None) -> list[dict]:
    """Merge a candidate. Descriptions accumulate; everything else must validate."""
    errors = []
    if not candidate:
        return errors
    data = dict(candidate)
    description = data.pop("description", None)
    errors.extend(merge_fields(intake, data))
    if description is None or str(description).strip() == "":
        return errors
    ok, normalized, code = normalize_field("description", description)
    if not ok:
        if code and code != "empty":
            errors.append({"field": "description", "code": code, "value": str(description)[:120]})
        return errors
    current = intake.get("description")
    if not current:
        intake["description"] = normalized
    elif normalized in current or current in normalized:
        intake["description"] = normalized if len(normalized) >= len(current) else current
    else:
        intake["description"] = f"{current} {normalized}"[:600]
    return errors


def merge_fields(intake: dict, candidate: dict | None) -> list[dict]:
    """Keep only values that pass validation. Return rejected attempts."""
    errors = []
    if not candidate:
        return errors
    for key, value in candidate.items():
        if key not in intake or value is None or value == "":
            continue
        ok, normalized, code = normalize_field(key, value)
        if ok and normalized:
            intake[key] = normalized
        elif code and code != "empty":
            errors.append({"field": key, "code": code, "value": str(value)[:120]})
    return errors
