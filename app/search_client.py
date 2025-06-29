from google.cloud.firestore import Client
from collections import Counter
import math, re

_db: Client | None = None
_REGEX = re.compile(r"[a-zA-Zа-яА-Я0-9]+")

def _get_db() -> Client:
    global _db
    if _db is None:
        _db = Client()
    return _db

def _tokenize(txt: str) -> list[str]:
    return [t.lower() for t in _REGEX.findall(txt)]

def _bm25_score(tokens_q: list[str], tokens_d: list[str]) -> float:
    tf = Counter(tokens_d)
    score = 0.0
    for t in tokens_q:
        if t in tf:
            score += tf[t] / (tf[t] + 1)
    return score / (len(tokens_d) or 1)

async def search(query: str, k: int = 3) -> list[dict]:
    q_tokens = _tokenize(query)
    docs = (
        _get_db()
        .collection("docs")
        .stream()
    )
    scored: list[tuple[float, dict]] = []
    for d in docs:
        data = d.to_dict()
        tokens = data.get("tokens") or _tokenize(data["text"])
        score = _bm25_score(q_tokens, tokens)
        if score > 0:
            scored.append((score, data))
    scored.sort(reverse=True, key=lambda x: x[0])
    return [d for _, d in scored[:k]]

