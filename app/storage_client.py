import os, uuid, pathlib

_BASE = pathlib.Path(__file__).parent.parent / "local_uploads"
_BASE.mkdir(exist_ok=True)

def put_file(name: str, data: bytes) -> str:
    fname = f"{uuid.uuid4().hex}_{os.path.basename(name)}"
    (_BASE / fname).write_bytes(data)
    return f"/files/{fname}"

def get_file(name: str) -> bytes:
    return (_BASE / name).read_bytes()

