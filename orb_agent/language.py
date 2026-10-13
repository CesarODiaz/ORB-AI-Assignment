"""Language detection that does not depend on the model."""

from orb_agent.textutil import fold, tokens

_ES = {
    "hola", "gracias", "necesito", "pedido", "lampara", "mueble", "roto",
    "rota", "quiero", "soy", "correo", "telefono", "urgente", "garantia",
    "precio", "cita", "taller", "arreglo", "chispa", "factura", "manana",
    "tarde", "pieza", "restaurar", "nombre", "llamo",
}
_EN = {
    "hello", "hi", "thanks", "thank", "need", "order", "lamp", "furniture",
    "broken", "please", "email", "phone", "urgent", "warranty", "price",
    "appointment", "workshop", "repair", "spark", "invoice", "morning",
    "afternoon", "piece", "restore", "name",
}


def detect_language(text: str, previous: str = "en") -> str:
    words = tokens(text)
    if not words:
        return previous if previous in {"es", "en"} else "en"
    spanish = len(words & _ES)
    english = len(words & _EN)
    if spanish > english:
        return "es"
    if english > spanish:
        return "en"
    return previous if previous in {"es", "en"} else "en"
