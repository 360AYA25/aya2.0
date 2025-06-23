from fastapi import APIRouter, Request
from fastapi.responses import FileResponse
from telegram import Update, InputFile
from telegram.ext import (
    Application,
    ContextTypes,
    AIORateLimiter,
    MessageHandler,
    CommandHandler,
    filters,
)
import os, openai, aiofiles
from app.firestore_client import save_dialog
from app.state import set_topic, get_topic
from app.storage_client import put_file

router = APIRouter()

openai.api_key = os.environ["OPENAI_KEY"]
TOKEN = os.environ["TELEGRAM_TOKEN"]

tg_app = (
    Application.builder()
    .token(TOKEN)
    .rate_limiter(AIORateLimiter())
    .build()
)


async def gpt_reply(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    pass  # твой обработчик


@router.post("/webhook/telegram")
async def webhook(req: Request):
    data = await req.json()
    update = Update.de_json(data, tg_app.bot)
    await tg_app.process_update(update)
    return {"ok": True}


def build_app():
    return tg_app

