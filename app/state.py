# ► app/state.py   (замените целиком)
from app.firestore_client import _db

async def set_topic(user_id: str, topic: str) -> None:
    await _db.collection("users").document(user_id).set({"topic": topic})

async def get_topic(user_id: str) -> str:
    doc = await _db.collection("users").document(user_id).get()
    return doc.to_dict().get("topic", "default") if doc.exists else "default"

