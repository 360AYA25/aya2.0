from app.firestore_client import _db

_topic_cache: dict[str, str] = {}


async def set_topic(user_id: str, topic: str) -> None:
    _topic_cache[user_id] = topic
    await _db.collection("users").document(user_id).set({"topic": topic})


async def get_topic(user_id: str) -> str:
    if user_id in _topic_cache:
        return _topic_cache[user_id]
    doc = await _db.collection("users").document(user_id).get()
    topic = doc.to_dict().get("topic", "default") if doc.exists else "default"
    _topic_cache[user_id] = topic
    return topic

