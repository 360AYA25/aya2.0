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


async def set_system_prompt(topic: str, prompt: str) -> None:
    await _db.collection("topics").document(topic).set({"system_prompt": prompt})


async def get_system_prompt(topic: str) -> str:
    doc = await _db.collection("topics").document(topic).get()
    return doc.to_dict().get("system_prompt", "") if doc.exists else ""

