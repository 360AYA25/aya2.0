from google.cloud.firestore_async import AsyncClient
import datetime

_client: AsyncClient | None = None


def _get_client() -> AsyncClient:
    global _client
    if _client is None:
        _client = AsyncClient()
    return _client


async def save_dialog(user_id: str, user_msg: str, bot_msg: str):
    await _get_client()\
        .collection("dialogs")\
        .document(user_id)\
        .collection("messages")\
        .add(
            {
                "ts": datetime.datetime.utcnow(),
                "user": user_msg,
                "bot": bot_msg,
            }
        )


async def get_dialog_page(user_id: str, page: int = 1, limit: int = 20):
    snap = await (
        _get_client()
        .collection("dialogs")
        .document(user_id)
        .collection("messages")
        .order_by("ts", direction="DESCENDING")
        .offset((page - 1) * limit)
        .limit(limit)
        .get()
    )
    return [d.to_dict() for d in snap]


async def set_topic(user_id: str, topic: str):
    await _get_client()\
        .collection("users")\
        .document(user_id)\
        .set({"topic": topic}, merge=True)

