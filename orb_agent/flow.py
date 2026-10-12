"""Decide when a review can be closed without asking the model."""

import re

from orb_agent.textutil import fold

_CONFIRM_STARTS = (
    "si",
    "yes",
    "ok",
    "okay",
    "vale",
    "confirmo",
    "confirmado",
    "confirm",
    "confirmed",
    "correcto",
    "de acuerdo",
    "adelante",
    "perfecto",
    "eso es",
    "eso es todo",
    "thats right",
    "that's right",
    "looks good",
    "sounds good",
)
_REJECT_STARTS = (
    "no",
    "cambia",
    "cambialo",
    "incorrecto",
    "mal",
    "wrong",
    "change",
    "corregir",
    "corregid",
    "wait",
)
_HARD_REJECT = ("no es correcto", "not correct", "datos mal", "esta mal", "está mal")


def _starts(folded: str, words: tuple[str, ...]) -> bool:
    for word in words:
        if folded == word or folded.startswith(word + " ") or folded.startswith(word + ","):
            return True
    return False


def is_pure_confirmation(text: str) -> bool:
    folded = fold(text).strip(" .!")
    if not folded or len(folded) > 80:
        return False
    if "@" in text or re.search(r"\d[\d\s.\-]{8,}\d", text):
        return False
    if any(phrase in folded for phrase in _HARD_REJECT):
        return False
    words = set(folded.replace(",", " ").split())
    if words & {"pero", "but", "cambia", "change", "incorrecto", "wrong", "mal", "error"}:
        return False
    return _starts(folded, _CONFIRM_STARTS)


def is_rejection(text: str) -> bool:
    folded = fold(text).strip(" .!")
    if any(phrase in folded for phrase in _HARD_REJECT):
        return True
    return _starts(folded, _REJECT_STARTS)
