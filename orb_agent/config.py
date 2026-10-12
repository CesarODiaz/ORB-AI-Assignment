"""Shared constants for the ORB Atelier intake agent."""

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
KNOWLEDGE_PATH = ROOT / "knowledge" / "articles.json"
STATIC_DIR = ROOT / "docs"
DEFAULT_DATA_DIR = ROOT / "data" / "conversations"

OLLAMA_HOST = "http://127.0.0.1:11434"
DEFAULT_MODEL = "llama3.2"
DEFAULT_PORT = 8765

ITEM_TYPES = ("lamp", "furniture", "textile", "other")
CATEGORIES = (
    "damage",
    "finish",
    "electrical",
    "parts",
    "scheduling",
    "billing",
    "other",
)
URGENCIES = ("low", "medium", "high", "critical")
CONTACT_WINDOWS = ("morning", "afternoon", "evening", "any")
SENTIMENTS = ("calm", "neutral", "frustrated", "angry")
LANGUAGES = ("es", "en")

INTAKE_FIELDS = (
    "customer_name",
    "contact_email",
    "contact_phone",
    "reference_code",
    "item_type",
    "category",
    "description",
    "urgency",
    "preferred_contact",
)

REQUIRED_FIELDS = (
    "customer_name",
    "contact",
    "item_type",
    "category",
    "description",
    "urgency",
)
