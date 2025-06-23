from fastapi import APIRouter, Request
from telegram import Update, InputFile
from telegram.ext import (
    Application,
    ContextTypes,
    MessageHandler,
    CommandHandler,
    filters,
    AIORateLimiter,
)
import os, uuid

from app.firestore_client import save_dialog, get_dialog_page, set_topic
from app.storage_client import put_file
from app.doc_summarizer import summarize     # ⬅️ NEW
from app.openai_client import ask_gpt        # existing helper

router = APIRouter()

TOKEN = os.environ["TELEGRAM_TOKEN"]

tg_app = (
    Application.builder()
    .token(TOKEN)
    .rate_limiter(AIORateLimiter())
    .build()
)


# ───── COMMANDS ────────────────────────────────────────────────────────────────
async def cmd_topic(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not ctx.args:
        await update.message.reply_text("usage: /topic <name>")
        return
    await set_topic(str(update.effective_user.id), ctx.args[0])
    await update.message.reply_text("✓ Topic switched to " + ctx.args[0])


async def cmd_history(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    page = await get_dialog_page(str(update.effective_user.id), 0)
    formatted = "\n\n".join(f"🧑 {u}\n🤖 {b}" for u, b in page)
    await update.message.reply_text(formatted or "— empty —")


async def cmd_upload(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.document:
        await update.message.reply_text("Attach a file with /upload")
        return
    doc = update.message.document
    raw = await (await ctx.bot.get_file(doc.file_id)).download_as_bytearray()
    ext = os.path.splitext(doc.file_name)[1]
    name = f"{uuid.uuid4().hex}{ext}"
    url = await put_file(name, bytes(raw))
    await update.message.reply_text(f"✓ uploaded → {url}")


async def cmd_summarize(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.document:
        await update.message.reply_text("Attach a file with /summarize")
        return
    await update.message.reply_text("⏳ summarizing…")
    doc = update.message.document
    raw = await (await ctx.bot.get_file(doc.file_id)).download_as_bytearray()
    try:
        summary = await summarize(bytes(raw), doc.file_name)
        await update.message.reply_text(summary)
    except ValueError:
        await update.message.reply_text("Unsupported file type (pdf / txt / md)")


# register
tg_app.add_handler(CommandHandler("topic", cmd_topic))
tg_app.add_handler(CommandHandler("history", cmd_history))
tg_app.add_handler(CommandHandler("upload", cmd_upload))
tg_app.add_handler(CommandHandler("summarize", cmd_summarize))


# ───── FASTAPI BRIDGE ─────────────────────────────────────────────────────────
@router.post("/webhook/telegram")
async def webhook(request: Request):
    update = Update.de_json(await request.json(), tg_app.bot)
    await tg_app.process_update(update)
    return {"ok": True}

