"""Lexical retrieval over the workshop notes. No embedding model is required."""

import json

from orb_agent.config import KNOWLEDGE_PATH
from orb_agent.textutil import clip, tokens

_STOP = {
    "el", "la", "los", "las", "un", "una", "de", "del", "al", "y", "o", "que",
    "en", "por", "para", "con", "mi", "me", "se", "es", "lo", "su", "sus",
    "the", "a", "an", "of", "and", "or", "to", "for", "in", "on", "my", "is",
    "it", "this", "that", "please", "hola", "hello", "gracias", "thanks",
    "orb", "atelier", "valencia",
}
_SAFETY = {"chispa", "chispas", "humo", "spark", "sparks", "smoke", "quemado", "quemad"}


class KnowledgeBase:
    def __init__(self, articles: list[dict]):
        self.articles = articles

    @classmethod
    def load(cls, path=KNOWLEDGE_PATH) -> "KnowledgeBase":
        payload = json.loads(path.read_text(encoding="utf-8"))
        return cls(payload["articles"])

    def search(self, query: str, lang: str, limit: int = 2) -> list[dict]:
        query_tokens = tokens(query) - _STOP
        if not query_tokens:
            return []
        scored = []
        for article in self.articles:
            if article["lang"] != lang:
                continue
            tag_tokens = tokens(" ".join(article.get("tags", [])))
            body_tokens = tokens(f"{article['title']} {article['body']}") | tag_tokens
            overlap = query_tokens & body_tokens
            tag_hits = query_tokens & tag_tokens
            if not overlap and not tag_hits:
                continue
            score = len(overlap) + (2 * len(tag_hits))
            if score < 1:
                continue
            if score < 2 and not tag_hits and len(query_tokens) > 2:
                continue
            scored.append((score, article))
        scored.sort(key=lambda item: item[0], reverse=True)
        results = [self._view(article, score) for score, article in scored[:limit]]
        if query_tokens & _SAFETY:
            safety = next(
                (article for article in self.articles if article["id"] == f"electrical-{lang}"),
                None,
            )
            if safety is not None:
                forced = self._view(safety, 6)
                results = [forced, *[item for item in results if item["id"] != forced["id"]]]
                results = results[:limit]
        return results

    def _view(self, article: dict, score: int) -> dict:
        return {
            "id": article["id"],
            "title": article["title"],
            "snippet": clip(article["body"], 280),
            "score": score,
        }
