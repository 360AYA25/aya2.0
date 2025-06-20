from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.telegram_adapter import router as tg_router

app = FastAPI()
app.include_router(tg_router)

# локальные файлы, загруженные через /upload
app.mount("/files", StaticFiles(directory="local_uploads"), name="files")

