import os
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "/etc/secrets/service-account.json"

import datetime
from google.cloud.firestore import AsyncClient

_db: AsyncClient | None = None

def _get_db() -> AsyncClient | None:
    global _db
    if _db is None:
        _db = AsyncClient()
    return _db

async def save_dialog(uid: str, user_msg: str, bot_msg: str):
    db = _get_db()
    if db is not None:
        col = db.collection("dialogs").document(uid).collection("msgs")
        ts = datetime.datetime.utcnow()
        await col.add({"user": user_msg, "bot": bot_msg, "ts": ts})

async def get_dialog_page(uid: str, page: int, size: int = 10):
    db = _get_db()
    if db is not None:
        col = (
            db.collection("dialogs")
            .document(uid)
            .collection("msgs")
            .order_by("ts", direction="DESCENDING")
            .limit(size)
            .offset(page * size)
        )
        docs = await col.get()
        return [d.to_dict() for d in docs]
    return []

async def get_dialog_total(uid: str) -> int:
    db = _get_db()
    if db is not None:
        col = (
            db.collection("dialogs")
            .document(uid)
            .collection("msgs")
        )
        return len(await col.get())
    return 0

async def set_topic(uid: str, topic: str):
    db = _get_db()
    if db is not None:
        await db.collection("topics").document(uid).set({"topic": topic})

async def get_topic(uid: str):
    db = _get_db()
    if db is not None:
        doc = await db.collection("topics").document(uid).get()
        return (doc.to_dict() or {}).get("topic")
    return None

