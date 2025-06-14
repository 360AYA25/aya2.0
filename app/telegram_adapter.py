from fastapi import APIRouter, Request, HTTPException
from telegram import Update
from telegram.ext import (
    Application,
    ContextTypes,
    AIORateLimiter,
    MessageHandler,
    filters,
)
import os, logging, openai

router = APIRouter()

TOKEN = os.environ["TELEGRAM_TOKEN"]
OPENAI_KEY = os.environ["OPENAI_KEY"]
openai.api_key = OPENAI_KEY

tg_app = (
    Application.builder()
    .token(TOKEN)
    .rate_limiter(AIORateLimiter())
    .build()
)

# webhook endpoint -------------------------------------------------
@router.post("/webhook/telegram")
async def telegram_webhook(req: Request):
    try:
        data = await req.json()
        update = Update.de_json(data, tg_app.bot)
        await tg_app.initialize()
        await tg_app.process_update(update)
        return {"ok": True}
    except Exception as e:
        logging.exception("telegram webhook error")
        raise HTTPException(500, str(e))

# echo / GPT handler -----------------------------------------------
async def reply(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return
    text = update.message.text or ""
    # простой эхо-ответ (позже вставим GPT-логику)
    await update.message.reply_text(text)

tg_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, reply))
