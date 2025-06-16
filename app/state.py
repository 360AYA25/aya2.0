_topic_cache: dict[str, str] = {}

async def set_topic(user_id: str, topic: str) -> None:
    _topic_cache[user_id] = topic

async def get_topic(user_id: str) -> str:
    return _topic_cache.get(user_id, "default")

