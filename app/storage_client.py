from google.cloud.storage import Client
from uuid import uuid4
import mimetypes, os, asyncio

_BUCKET = os.environ["GCS_BUCKET"]
_PUBLIC = f"https://storage.googleapis.com/{_BUCKET}"
_client: Client | None = None


def _get_client():
    global _client
    if _client is None:
        _client = Client()
    return _client


async def put_file(name: str, data: bytes) -> str:
    loop = asyncio.get_running_loop()
    await loop.run_in_executor(None, _upload_sync, name, data)
    return f"{_PUBLIC}/{name}"


def _upload_sync(name: str, data: bytes):
    blob = _get_client().bucket(_BUCKET).blob(name)
    blob.upload_from_string(data, content_type=mimetypes.guess_type(name)[0] or "application/octet-stream")

