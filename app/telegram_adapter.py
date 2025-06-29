from fastapi import APIRouter, Request
from telegram import Update
from telegram.ext import (
    ApplicationBuilder, ContextTypes, AIORateLimiter,
    CommandHandler, MessageHandler, filters
)
import uuid
import os
import logging
import asyncio

from app.firestore_client import (
    save_dialog, get_dialog_page, get_dialog_total, set_topic, get_topic
)
from app.storage_client import put_file
from app.doc_summarizer import summarize
from app.openai_client import ask_gpt
from app.search_client import search

router = APIRouter()
HISTORY_PAGE_SIZE = 10
UPLOAD_LIMIT = 10 * 1024 * 1024
ALLOWED_EXTS = (".pdf", ".txt", ".md")

# === HANDLERS ===

async def cmd_ping(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("pong")

async def cmd_topic(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not ctx.args:
        await update.message.reply_text("usage: /topic <name>")
        return
    await set_topic(str(update.effective_user.id), ctx.args[0])
    await update.message.reply_text("✓ Topic switched to " + ctx.args[0])

async def cmd_history(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    try:
        uid = str(update.effective_user.id)
        page = await get_dialog_page(uid, 0)
        formatted = "\n\n".join(f"🧑 {u}\n🤖 {b}" for u, b in page)
        await update.message.reply_text(formatted or "— empty —")
    except Exception as e:
        await update.message.reply_text(f"❗️Error in /history: {e}")

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
        await update.message.reply_text(summary)
    except Exception as e:
        await update.message.reply_text(f"❗️Error: {e}")

async def cmd_search(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not ctx.args:
        await update.message.reply_text("usage: /search <query>")
        return
    query = " ".join(ctx.args)
    if len(query) > 256:
        await update.message.reply_text("Query too long (≤ 256 chars)")
        return
    hits = await search(query)
    if not hits:
        await update.message.reply_text("— no matches —")
        return
    context = "\n\n".join(h["text"][:2000] for h in hits)
    answer = await ask_gpt(query, context)
    links = "\n".join(f"• {h['title']} — {h['url']}" for h in hits)
    await update.message.reply_text(f"{answer}\n\n{links}")

async def text_handler(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if update.effective_user and update.message and update.message.text:
        uid = str(update.effective_user.id)
        topic = await get_topic(uid) or "default"
        reply = await ask_gpt(update.message.text, topic)
        await save_dialog(uid, update.message.text, reply)
        await update.message.reply_text(reply)

# === FASTAPI/TELEGRAM INITIALIZATION ===

async def create_tg_app(token: str):
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
    app.add_handler(CommandHandler("search", cmd_search))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_handler))
    return app

# ——— Добавь это в startup FastAPI ———
def setup_tg_app(app):  # app = FastAPI instance
    @app.on_event("startup")
    async def on_startup():
        token = os.environ["TELEGRAM_TOKEN"]
        tg_app = await create_tg_app(token)
        await tg_app.initialize()  # <<< КРИТИЧЕСКО!
        app.state.tg_app = tg_app

# === FASTAPI ENDPOINT ===

@router.post("/webhook/telegram")
async def webhook(request: Request):
    update = Update.de_json(await request.json(), request.app.state.tg_app.bot)
    await request.app.state.tg_app.process_update(update)
    return {"ok": True}
