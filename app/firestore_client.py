import os, json
from google.cloud.firestore import AsyncClient
from google.oauth2 import service_account

_creds = service_account.Credentials.from_service_account_info(
    json.loads(os.environ["GOOGLE_APPLICATION_CREDENTIALS_JSON"])
)
_db = AsyncClient(credentials=_creds, project=_creds.project_id)

async def save_dialog(user_id: str, message: dict):
    await _db.collection("dialogs") \
             .document(user_id) \
             .collection("messages") \
             .add(message)
