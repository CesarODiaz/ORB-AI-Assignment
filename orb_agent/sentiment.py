"""Lexicon sentiment. The model may raise the score, never lower a strong signal."""

from orb_agent.textutil import fold

_ANGRY = (
    "estafa", "indign", "furios", "denuncia", "ridiculous", "outraged",
    "angry", "worst service", "pesimo", "inaceptable", "inacceptable",
)
_FRUSTRATED = (
    "harta", "harto", "molesto", "molesta", "cansad", "frustr", "waiting forever",
    "sigue igual", "no me haceis", "no me hacen", "useless", "annoyed",
    "todavia no", "still waiting", "otra vez",
)
_CALM = (
    "gracias", "perfecto", "genial", "estupendo", "thanks", "thank you",
    "great", "lovely", "perfecto",
)


def lexicon_sentiment(text: str) -> str:
    folded = fold(text)
    if any(mark in folded for mark in _ANGRY):
        return "angry"
    if any(mark in folded for mark in _FRUSTRATED):
        return "frustrated"
    if any(mark in folded for mark in _CALM):
        return "calm"
    return "neutral"


def sticky(previous: str | None, proposed: str) -> str:
    """Keep a frustration signal once it has appeared in the conversation."""
    rank = {"calm": 0, "neutral": 1, "frustrated": 2, "angry": 3}
    if previous in {"frustrated", "angry"} and rank.get(previous, 1) > rank.get(proposed, 1):
        return previous
    return proposed


def combine_sentiment(lexicon: str, model_value: str | None) -> str:
    """Prefer frustration. A cheerful model reply must not hide it."""
    if "angry" in {lexicon, model_value}:
        return "angry"
    if "frustrated" in {lexicon, model_value}:
        return "frustrated"
    if model_value in {"calm", "neutral"}:
        return model_value
    return lexicon
