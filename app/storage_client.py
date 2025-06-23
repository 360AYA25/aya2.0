import os, json
from google.cloud.storage import Client
from google.oauth2 import service_account

_creds = service_account.Credentials.from_service_account_info(
    json.loads(os.environ["GOOGLE_APPLICATION_CREDENTIALS_JSON"])
)
_client = Client(credentials=_creds, project=_creds.project_id)
_bucket = _client.bucket(os.environ["GCS_BUCKET"])   # имя бакета

async def put_file(path: str, data: bytes) -> str:
    blob = _bucket.blob(path)
    blob.upload_from_string(data)
    blob.make_public()
    return blob.public_url  # https://storage.googleapis.com/...

async def get_file(path: str) -> bytes:
    blob = _bucket.blob(path)
    return blob.download_as_bytes()

