from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.telegram_adapter import router as tg_router

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(tg_router)

