from fastapi import APIRouter, Request, HTTPException
from telegram import Update
from telegram.ext import (
    Application,
    ContextTypes,
    AIORateLimiter,
    MessageHandler,
    filters,
)
import os, logging
import openai

# -------- GPT helper --------
async def ask_gpt(prompt: str) -> str:
    """Отправляет запрос в GPT-4o и возвращает ответ одной строкой."""
    resp = await openai.ChatCompletion.acreate(       # ← асинхронно!
        model="gpt-4o-mini",                          # самый дешёвый 4o-вариант
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7,
        max_tokens=500,
    )
    return resp.choices[0].message.content.strip()
# ----------------------------

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

async def gpt_reply(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
# if update.message:                                   # только текст
        user_text = update.message.text.strip()
        bot_answer = await ask_gpt(user_text)            # GPT-4o
        await update.message.reply_text(bot_answer)

 tg_app.add_handler(
    MessageHandler(filters.TEXT & ~filters.COMMAND, gpt_reply)
)

# async def reply(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
   # if not update.message:
       # return
   # text = update.message.text or ""
    # простой эхо-ответ (позже вставим GPT-логику)
   # await update.message.reply_text(text)

# tg_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, reply))
