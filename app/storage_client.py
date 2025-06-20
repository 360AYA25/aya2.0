import os, json, uuid
from google.cloud.storage import Client
from google.oauth2 import service_account

_creds = service_account.Credentials.from_service_account_info(
    json.loads(os.environ["GOOGLE_APPLICATION_CREDENTIALS_JSON"])
)
_storage = Client(credentials=_creds, project=_creds.project_id)
_BUCKET = os.environ["GCS_BUCKET"]        # example: aya-files

async def put_file(fname: str, data: bytes) -> str:
    blob_id = f"{uuid.uuid4()}_{fname}"
    bucket = _storage.bucket(_BUCKET)
    bucket.blob(blob_id).upload_from_string(data)
    return blob_id

