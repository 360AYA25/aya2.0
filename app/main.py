# app/main.py
from fastapi import FastAPI

# Telegram webhook routes
from app.telegram_adapter import router as tg_router

app = FastAPI()
app.include_router(tg_router)

