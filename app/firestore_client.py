import os, datetime
from google.cloud.firestore import AsyncClient   

_db: AsyncClient | None = None


def _get_db() -> AsyncClient:
    global _db
    if _db is None:
        _db = AsyncClient()
    return _db


async def save_dialog(uid: str, user_msg: str, bot_msg: str):
    col = _get_db().collection("dialogs").document(uid).collection("msgs")
    ts = datetime.datetime.utcnow()
    await col.add({"user": user_msg, "bot": bot_msg, "ts": ts})


async def get_dialog_page(uid: str, page: int, size: int = 10):
    col = (
        _get_db()
        .collection("dialogs")
        .document(uid)
        .collection("msgs")
        .order_by("ts", direction="DESCENDING")
        .limit(size)
        .offset(page * size)
    )
    docs = await col.get()
    return [d.to_dict() for d in docs]


async def set_topic(uid: str, topic: str):
    await _get_db().collection("topics").document(uid).set({"topic": topic})


async def get_topic(uid: str):
    doc = await _get_db().collection("topics").document(uid).get()
    return (doc.to_dict() or {}).get("topic")

