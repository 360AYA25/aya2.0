import os, json
from google.cloud.firestore import AsyncClient
from google.oauth2 import service_account
from google.cloud.firestore_v1 import SERVER_TIMESTAMP

_creds = service_account.Credentials.from_service_account_info(
    json.loads(os.environ["GOOGLE_APPLICATION_CREDENTIALS_JSON"])
)
_db = AsyncClient(credentials=_creds, project=_creds.project_id)

async def save_dialog(user_text: str, bot_text: str, *, topic: str = "default"):
    await (
        _db.collection("dialogs")
        .document(topic)
        .collection("messages")
        .add({"user": user_text, "bot": bot_text, "time": SERVER_TIMESTAMP})
    )

async def get_last_dialog(topic: str, limit: int = 6):
    docs = (
        await _db.collection("dialogs")
        .document(topic)
        .collection("messages")
        .order_by("time", direction="DESCENDING")
        .limit(limit)
        .get()
    )
    return [d.to_dict() for d in docs][::-1]

_prompt_cache: dict[str, str] = {}

async def set_prompt(topic: str, prompt: str):
    await _db.collection("prompts").document(topic).set(
        {"prompt": prompt, "updated_at": SERVER_TIMESTAMP}
    )
    _prompt_cache[topic] = prompt

async def get_prompt(topic: str) -> str:
    if topic in _prompt_cache:
        return _prompt_cache[topic]
    doc = await _db.collection("prompts").document(topic).get()
    text = doc.to_dict().get("prompt", "") if doc.exists else ""
    _prompt_cache[topic] = text
    return text

async def reload_prompt(topic: str) -> str:
    _prompt_cache.pop(topic, None)
    return await get_prompt(topic)

async def add_file_meta(blob_id: str, fname: str, user_id: str):
    await _db.collection("files").add(
        {"blob": blob_id, "name": fname, "user": user_id, "time": SERVER_TIMESTAMP}
    )

