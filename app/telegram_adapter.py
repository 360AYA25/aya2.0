from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import FileResponse              # new
from telegram import Update
from telegram.ext import (
    Application,
    ContextTypes,
    AIORateLimiter,
    MessageHandler,
    CommandHandler,
    filters,
)
import os, logging
import openai

from .firestore_client import save_dialog
from app.state import set_topic, get_topic

# ===== static settings ==========================
TOPIC = "christianity"            # default
ROADMAP_URL = (
    "https://raw.githubusercontent.com/360AYA25/aya2.0/main/"
    "docs/roadmap/Aya%20Bot%20—%20Roadmap%20v0.3%2016.06.pdf"
)
# ===============================================

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

# ---------- /topic <name> -----------------------------------
async def cmd_topic(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Usage: /topic <name>")
        return
    topic = context.args[0]
    await set_topic(str(update.effective_user.id), topic)
    await update.message.reply_text(f"✓ Topic switched to {topic}")

tg_app.add_handler(CommandHandler("topic", cmd_topic))

# ---------- /roadmap ----------------------------------------
async def cmd_roadmap(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send latest Roadmap PDF."""
    await update.message.reply_document(document=ROADMAP_URL)

tg_app.add_handler(CommandHandler("roadmap", cmd_roadmap))

# ---------- HTTP endpoint for same PDF ----------------------
@router.get("/roadmap/latest")
async def get_latest_roadmap():
    return FileResponse(
        "docs/roadmap/Aya Bot — Roadmap v0.3 16.06.pdf",
        media_type="application/pdf",
        filename="Roadmap_v0.3.pdf",
    )

# ---------- webhook endpoint --------------------------------
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

# ---------- GPT reply handler -------------------------------
async def ask_gpt(prompt: str) -> str:
    resp = await openai.ChatCompletion.acreate(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7,
        max_tokens=500,
    )
    return resp.choices[0].message.content.strip()


async def gpt_reply(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return
    user_text = update.message.text.strip()
    bot_answer = await ask_gpt(user_text)
    topic = await get_topic(str(update.effective_user.id))
    await save_dialog(user_text, bot_answer, topic=topic)
    await update.message.reply_text(bot_answer)


tg_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, gpt_reply))

