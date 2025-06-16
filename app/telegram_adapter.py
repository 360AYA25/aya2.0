from fastapi import APIRouter, Request
from fastapi.responses import FileResponse
from telegram import Update
from telegram.ext import (
    Application, ContextTypes, AIORateLimiter,
    MessageHandler, CommandHandler, filters
)
import os, openai, textwrap
from app.firestore_client import save_dialog, get_last_dialog
from app.state            import set_topic, get_topic

ROADMAP_FILE = "docs/roadmap/Aya Bot — Roadmap v0.3.pdf"
router = APIRouter()

TOKEN          = os.environ["TELEGRAM_TOKEN"]
openai.api_key = os.environ["OPENAI_KEY"]

tg_app = (
    Application.builder()
    .token(TOKEN)
    .rate_limiter(AIORateLimiter())
    .build()
)

# ────────────────── GPT helper
async def ask_gpt(prompt: str) -> str:
    r = await openai.ChatCompletion.acreate(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7,
        max_tokens=500,
    )
    return r.choices[0].message.content.strip()

# ────────────────── /topic
async def cmd_topic(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not ctx.args:
        await update.message.reply_text("Usage: /topic <name>")
        return
    topic = ctx.args[0]
    await set_topic(str(update.effective_user.id), topic)
    await update.message.reply_text(f"✓ Topic switched to {topic}")

tg_app.add_handler(CommandHandler("topic", cmd_topic))

# ────────────────── /echo
async def cmd_echo(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not ctx.args:
        await update.message.reply_text("Usage: /echo <text>")
        return
    user_text = " ".join(ctx.args)
    topic     = await get_topic(str(update.effective_user.id))
    await save_dialog(user_text, user_text, topic=topic)
    await update.message.reply_text(user_text)

tg_app.add_handler(CommandHandler("echo", cmd_echo))

# ────────────────── /history
async def cmd_history(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    topic = await get_topic(str(update.effective_user.id))
    history = await get_last_dialog(topic)
    if not history:
        await update.message.reply_text("— empty —")
        return
    lines = [f"👤 {d['user']}\n🤖 {d['bot']}" for d in history]
    await update.message.reply_text("\n\n".join(lines))

tg_app.add_handler(CommandHandler("history", cmd_history))

# ────────────────── /roadmap
async def cmd_roadmap(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_document(document=open(ROADMAP_FILE, "rb"))

tg_app.add_handler(CommandHandler("roadmap", cmd_roadmap))

# ────────────────── GPT reply (обычный текст)
async def gpt_reply(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return
    user_text = update.message.text.strip()
    topic     = await get_topic(str(update.effective_user.id))
    bot_text  = await ask_gpt(user_text)
    await save_dialog(user_text, bot_text, topic=topic)
    await update.message.reply_text(bot_text)

tg_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, gpt_reply))

# ────────────────── FastAPI endpoints
@router.post("/webhook/telegram")
async def telegram_webhook(req: Request):
    data = await req.json()
    update = Update.de_json(data, tg_app.bot)
    await tg_app.initialize()
    await tg_app.process_update(update)
    return {"ok": True}

@router.get("/roadmap/latest")
async def get_latest_roadmap():
    return FileResponse(ROADMAP_FILE, filename=os.path.basename(ROADMAP_FILE))

