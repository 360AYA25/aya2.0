from fastapi import APIRouter, Request, HTTPException
from telegram import Update
from telegram.ext import Application, ContextTypes, AIORateLimiter
import openai, os, logging

# ====== keys & clients ======
openai.api_key = os.environ["OPENAI_KEY"]
TOKEN = os.environ["TELEGRAM_TOKEN"]

# ====== telegram setup ======
router = APIRouter()
tg_app = (
    Application.builder()
    .token(TOKEN)
    .rate_limiter(AIORateLimiter())
    .build()
)

# ====== webhook endpoint ======
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

# ====== message handler ======
@tg_app.message()
async def gpt_reply(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return
    user_text = update.message.text

    response = openai.ChatCompletion.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": "You are Aya, the helpful assistant."},
            {"role": "user", "content": user_text},
        ],
        temperature=0.7,
    )
    answer = response.choices[0].message.content.strip()
    await update.message.reply_text(answer)
