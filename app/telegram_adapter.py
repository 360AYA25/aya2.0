from fastapi import APIRouter, Request
from telegram import Update
from telegram.ext import (
    ApplicationBuilder, ContextTypes, AIORateLimiter,
    CommandHandler, MessageHandler, filters
)
import uuid
import os
import logging
from app.firestore_client import (
    save_dialog, get_dialog_page, get_dialog_total, set_topic, get_topic
)
from app.storage_client import put_file
from app.openai_client import ask_gpt
from app.doc_summarizer import summarize

router = APIRouter()
HISTORY_PAGE_SIZE = 10
UPLOAD_LIMIT = 10 * 1024 * 1024
ALLOWED_EXTS = (".pdf", ".txt", ".md")

# --- Handlers ---
async def cmd_ping(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("pong")

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
    try:
        raw = await (await ctx.bot.get_file(doc.file_id)).download_as_bytearray()
        summary = await summarize(bytes(raw), doc.file_name)
        if not summary or not summary.strip():
            await update.message.reply_text("Summary пустое или не удалось сгенерировать.")
        else:
            await update.message.reply_text(summary)
    except Exception as e:
        logging.warning(f"Ошибка в summarize: {e}")
        await update.message.reply_text(f"❗️ Ошибка при обработке файла: {e}")

# --- FastAPI Bridge ---
@router.post("/webhook/telegram")
async def webhook(request: Request):
    update = Update.de_json(await request.json(), tg_app.bot)
    await tg_app.process_update(update)
    return {"ok": True}

# --- TG App Build ---
TOKEN = os.environ.get("TELEGRAM_TOKEN")
tg_app = (
    ApplicationBuilder()
    .token(TOKEN)
    .rate_limiter(AIORateLimiter())
    .build()
)
tg_app.add_handler(CommandHandler("ping", cmd_ping))
tg_app.add_handler(CommandHandler("topic", cmd_topic))
tg_app.add_handler(CommandHandler("history", cmd_history))
tg_app.add_handler(CommandHandler("upload", cmd_upload))
tg_app.add_handler(CommandHandler("summarize", cmd_summarize))

async def build_app(token: str):
    app = (
        ApplicationBuilder()
        .token(token)
        .rate_limiter(AIORateLimiter())
        .build()
    )
    app.add_handler(CommandHandler("ping", cmd_ping))
    app.add_handler(CommandHandler("topic", cmd_topic))
    app.add_handler(CommandHandler("history", cmd_history))
    app.add_handler(CommandHandler("upload", cmd_upload))
    app.add_handler(CommandHandler("summarize", cmd_summarize))
    return app
