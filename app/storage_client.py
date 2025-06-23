from google.cloud.storage import Client
from google.cloud.exceptions import NotFound
from uuid import uuid4
import mimetypes
import os

_BUCKET = os.environ["GCS_BUCKET"]          # пример: aya360
_PUBLIC_URL = f"https://storage.googleapis.com/{_BUCKET}"

_client: Client | None = None


def _get_client() -> Client:
    global _client
    if _client is None:
        _client = Client()
    return _client


def put_file(path: str, data: bytes) -> str:
    """
    Сохраняет файл в бакет.
    path – относительный путь в бакете (например user123/file.pdf)
    data – содержимое.
    Возвращает публичный URL.
    """
    bucket = _get_client().bucket(_BUCKET)
    blob = bucket.blob(path)
    blob.upload_from_string(
        data,
        content_type=mimetypes.guess_type(path)[0] or "application/octet-stream",
    )
    # делаем файл публичным
    blob.make_public()
    return f"{_PUBLIC_URL}/{path}"


def get_file(path: str) -> bytes | None:
    """
    Возвращает содержимое файла или None, если нет.
    """
    bucket = _get_client().bucket(_BUCKET)
    blob = bucket.blob(path)
    try:
        return blob.download_as_bytes()
    except NotFound:
        return None

