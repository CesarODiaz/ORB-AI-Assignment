"""Deterministic summaries. The ticket text is never left to the model."""

_ITEM = {
    "es": {"lamp": "una lámpara", "furniture": "un mueble", "textile": "un tapizado", "other": "una pieza"},
    "en": {"lamp": "a lamp", "furniture": "a piece of furniture", "textile": "an upholstered piece", "other": "a piece"},
}
_CATEGORY = {
    "es": {
        "damage": "un daño",
        "finish": "el acabado",
        "electrical": "un fallo eléctrico",
        "parts": "una pieza que falta",
        "scheduling": "una cita",
        "billing": "una factura",
        "other": "otra consulta",
    },
    "en": {
        "damage": "damage",
        "finish": "the finish",
        "electrical": "an electrical fault",
        "parts": "a missing part",
        "scheduling": "an appointment",
        "billing": "an invoice",
        "other": "another request",
    },
}
_URGENCY = {
    "es": {"low": "baja", "medium": "media", "high": "alta", "critical": "crítica"},
    "en": {"low": "low", "medium": "medium", "high": "high", "critical": "critical"},
}
_WINDOW = {
    "es": {"morning": "por la mañana", "afternoon": "por la tarde", "evening": "por la noche", "any": "a cualquier hora"},
    "en": {"morning": "in the morning", "afternoon": "in the afternoon", "evening": "in the evening", "any": "at any time"},
}
_ITEM_LABEL = {
    "es": {"lamp": "Lámpara", "furniture": "Mueble", "textile": "Tapizado", "other": "Otra pieza"},
    "en": {"lamp": "Lamp", "furniture": "Furniture", "textile": "Upholstery", "other": "Other"},
}
_CATEGORY_LABEL = {
    "es": {
        "damage": "Daño",
        "finish": "Acabado",
        "electrical": "Fallo eléctrico",
        "parts": "Pieza que falta",
        "scheduling": "Cita",
        "billing": "Factura",
        "other": "Otra consulta",
    },
    "en": {
        "damage": "Damage",
        "finish": "Finish",
        "electrical": "Electrical fault",
        "parts": "Missing part",
        "scheduling": "Appointment",
        "billing": "Invoice",
        "other": "Other",
    },
}
_SENTIMENT = {
    "es": {"calm": "tranquilo", "neutral": "neutro", "frustrated": "frustrado", "angry": "enfadado"},
    "en": {"calm": "calm", "neutral": "neutral", "frustrated": "frustrated", "angry": "angry"},
}


def _lang(language: str) -> str:
    return "en" if language == "en" else "es"


def build_summary(record: dict) -> str:
    language = _lang(record.get("language", "es"))
    intake = record.get("intake") or {}
    name = intake.get("customer_name")
    item = _ITEM[language].get(intake.get("item_type") or "", "")
    category = _CATEGORY[language].get(intake.get("category") or "", "")
    urgency = _URGENCY[language].get(intake.get("urgency") or "", "")
    sentiment = _SENTIMENT[language].get(record.get("sentiment") or "neutral", "")
    contact = intake.get("contact_email") or intake.get("contact_phone") or ""
    reference = intake.get("reference_code")
    description = intake.get("description") or ""
    window = _WINDOW[language].get(intake.get("preferred_contact") or "", "")

    if language == "en":
        who = name or "The customer"
        parts = [f"{who} contacted ORB Atelier"]
        if item or category:
            parts.append(f"about {item or 'a piece'} ({category or 'unspecified'}).")
        else:
            parts.append("and the request is still incomplete.")
        if description:
            parts.append(f"Description: {description}")
        if urgency:
            parts.append(f"Urgency is {urgency}.")
        if reference:
            parts.append(f"Order {reference}.")
        if contact:
            parts.append(f"Contact: {contact}.")
        if window:
            parts.append(f"Preferred call {window}.")
        parts.append(f"Tone of the conversation: {sentiment}.")
        return " ".join(parts)

    who = name or "El cliente"
    parts = [f"{who} escribió a ORB Atelier"]
    if item or category:
        parts.append(f"por {item or 'una pieza'} ({category or 'sin clasificar'}).")
    else:
        parts.append("y la ficha todavía está incompleta.")
    if description:
        parts.append(f"Descripción: {description}")
    if urgency:
        parts.append(f"Urgencia {urgency}.")
    if reference:
        parts.append(f"Pedido {reference}.")
    if contact:
        parts.append(f"Contacto: {contact}.")
    if window:
        parts.append(f"Aviso {window}.")
    parts.append(f"Tono de la conversación: {sentiment}.")
    return " ".join(parts)


def confirmation_block(record: dict) -> str:
    language = _lang(record.get("language", "es"))
    intake = record["intake"]
    item = _ITEM_LABEL[language].get(intake.get("item_type") or "", "—")
    category = _CATEGORY_LABEL[language].get(intake.get("category") or "", "—")
    urgency = _URGENCY[language].get(intake.get("urgency") or "", "—")
    description = intake.get("description") or "—"
    if len(description) > 180:
        description = description[:179].rstrip() + "…"
    if language == "en":
        lines = [
            "Please confirm these details:",
            f"Name: {intake.get('customer_name')}",
            f"Email: {intake.get('contact_email') or '—'}",
            f"Phone: {intake.get('contact_phone') or '—'}",
            f"Order: {intake.get('reference_code') or 'new piece'}",
            f"Piece: {item}",
            f"Reason: {category}",
            f"Urgency: {urgency}",
            f"Description: {description}",
            "Reply yes to file the request, or tell me what to change.",
        ]
    else:
        lines = [
            "Confirma estos datos y lo dejo registrado:",
            f"Nombre: {intake.get('customer_name')}",
            f"Email: {intake.get('contact_email') or '—'}",
            f"Teléfono: {intake.get('contact_phone') or '—'}",
            f"Pedido: {intake.get('reference_code') or 'pieza nueva'}",
            f"Pieza: {item}",
            f"Motivo: {category}",
            f"Urgencia: {urgency}",
            f"Descripción: {description}",
            "Responde sí para cerrar la ficha, o dime qué hay que corregir.",
        ]
    return "\n".join(lines)


def closing_message(record: dict) -> str:
    language = _lang(record.get("language", "es"))
    ticket = record["ticket_id"]
    if language == "en":
        return (
            f"Done. Your request is filed as {ticket}. "
            "The workshop will use the contact you gave us. "
            "If the piece sparks or smells of burning, keep it unplugged."
        )
    return (
        f"Listo. Dejé la consulta registrada como {ticket}. "
        "El taller usará el contacto que nos diste. "
        "Si la pieza echa chispas o huele a quemado, mantenla desenchufada."
    )


def next_question(missing: list[str], language: str, errors: list[dict]) -> str:
    language = _lang(language)
    if any(item["code"] == "invalid_email" for item in errors):
        return (
            "That email does not look valid. Could you send it again?"
            if language == "en"
            else "Ese email no parece válido. ¿Me lo repites?"
        )
    if any(item["code"] == "invalid_phone" for item in errors):
        return (
            "That phone number does not look valid. Could you send it again?"
            if language == "en"
            else "Ese teléfono no parece válido. ¿Me lo repites?"
        )
    questions = {
        "es": {
            "customer_name": "¿Cómo te llamas?",
            "contact": "¿Me dejas un email o un teléfono para avisarte?",
            "item_type": "¿La pieza es una lámpara, un mueble o un tapizado?",
            "category": "¿Qué le pasa: daño, acabado, tema eléctrico, una pieza que falta, una cita o una factura?",
            "description": "Cuéntame con un poco de detalle qué ocurrió.",
            "urgency": "¿Qué urgencia tiene: baja, media, alta o crítica?",
        },
        "en": {
            "customer_name": "What is your name?",
            "contact": "What email or phone should we use to reach you?",
            "item_type": "Is the piece a lamp, furniture, or upholstery?",
            "category": "What is going on: damage, finish, electrical, a missing part, scheduling, or billing?",
            "description": "Tell me a little more about what happened.",
            "urgency": "How urgent is it: low, medium, high, or critical?",
        },
    }
    key = missing[0] if missing else "description"
    return questions[language][key]


def error_line(errors: list[dict], language: str) -> str:
    if not errors:
        return ""
    language = _lang(language)
    codes = {item["code"] for item in errors}
    if "invalid_email" in codes:
        return next_question([], language, errors)
    if "invalid_phone" in codes:
        return next_question([], language, errors)
    return ""
