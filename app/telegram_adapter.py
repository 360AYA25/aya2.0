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
from app.openai_client import ask_gpt
from app.doc_summarizer import summarize
from app.search_client import search

router = APIRouter()
HISTORY_PAGE_SIZE = 10
UPLOAD_LIMIT = 10 * 1024 * 1024
ALLOWED_EXTS = (".pdf", ".txt", ".md")

TOKEN = os.environ["TELEGRAM_TOKEN"]

tg_app = (
    ApplicationBuilder()
    .token(TOKEN)
    .rate_limiter(AIORateLimiter())
    .build()
)

# ——— HANDLERS ———

async def cmd_ping(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("pong")

async def cmd_topic(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    try:
        if not ctx.args:
            await update.message.reply_text("usage: /topic <name>")
            return
        await set_topic(str(update.effective_user.id), ctx.args[0])
        await update.message.reply_text("✓ Topic switched to " + ctx.args[0])
    except Exception as e:
        logging.warning(f"[topic] {e}")
        await update.message.reply_text(f"❗️Ошибка topic: {e}")

async def cmd_history(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    try:
        page = await get_dialog_page(str(update.effective_user.id), 0)
        formatted = "\n\n".join(f"🧑 {u}\n🤖 {b}" for u, b in page)
        await update.message.reply_text(formatted or "— empty —")
    except Exception as e:
        logging.warning(f"[history] {e}")
        await update.message.reply_text(f"❗️Ошибка history: {e}")

async def cmd_upload(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    try:
        if not update.message or not update.message.document:
            await update.message.reply_text("Attach a .pdf, .txt, or .md file with /upload")
            return
        doc = update.message.document
        ext = os.path.splitext(doc.file_name or "")[1].lower()
        if ext not in ALLOWED_EXTS:
            await update.message.reply_text(f"🚫 Unsupported file type ({ext})")
            logging.warning(f"Unsupported file type: {ext}")
            return
        file_size = doc.file_size if doc.file_size is not None else 0
        if file_size > UPLOAD_LIMIT:
            await update.message.reply_text("🚫 File too large (>10 MB)")
            logging.warning(f"File too large: {file_size} bytes")
            return 
        raw = await (await ctx.bot.get_file(doc.file_id)).download_as_bytearray()
        name = f"{uuid.uuid4().hex}{ext}"
        url = await put_file(name, bytes(raw))
        await update.message.reply_text(f"✓ uploaded → {url}")
    except Exception as e:
        logging.warning(f"[upload] {e}")
        await update.message.reply_text(f"❗️Ошибка upload: {e}")

async def cmd_search(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    try:
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
    except Exception as e:
        logging.warning(f"[search] {e}")
        await update.message.reply_text(f"❗️Ошибка search: {e}")

async def cmd_summarize(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    try:
        if not update.message or not update.message.document:
            await update.message.reply_text("Attach a .pdf, .txt или .md файл с /summarize")
            return
        doc = update.message.document
        filename = doc.file_name or "document"
        if not filename.lower().endswith((".pdf", ".txt", ".md")):
            await update.message.reply_text("Поддерживаются только PDF, TXT, MD (до 10 кБ)")
            return
        raw = await (await ctx.bot.get_file(doc.file_id)).download_as_bytearray()
        if len(raw) > 10_000:
            await update.message.reply_text("Файл слишком большой (до 10 кБ)")
            return
        # Если summarize async:
        try:
            summary = await summarize(bytes(raw), filename)
        except TypeError:
            # Если summarize sync:
            loop = asyncio.get_event_loop()
            summary = await loop.run_in_executor(None, summarize, bytes(raw), filename)
        if not summary or not summary.strip():
            await update.message.reply_text("Summary пустое или не удалось сгенерировать.")
        else:
            await update.message.reply_text(summary, parse_mode="Markdown")
    except Exception as e:
        logging.warning(f"[summarize] {e}")
        await update.message.reply_text(f"❗️Ошибка summarize: {e}")

async def text_handler(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    try:
        if update.effective_user and update.message and update.message.text:
            uid = str(update.effective_user.id)
            topic = await get_topic(uid) or "default"
            reply = await ask_gpt(update.message.text, topic)
            await save_dialog(uid, update.message.text, reply)
            await update.message.reply_text(reply)
    except Exception as e:
        logging.warning(f"[text_handler] {e}")
        await update.message.reply_text(f"❗️Ошибка text_handler: {e}")

# ——— РЕГИСТРАЦИЯ ХЕНДЛЕРОВ ———

tg_app.add_handler(CommandHandler("ping", cmd_ping))
tg_app.add_handler(CommandHandler("topic", cmd_topic))
tg_app.add_handler(CommandHandler("history", cmd_history))
tg_app.add_handler(CommandHandler("upload", cmd_upload))
tg_app.add_handler(CommandHandler("search", cmd_search))
tg_app.add_handler(CommandHandler("summarize", cmd_summarize))
tg_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_handler))

# ——— FASTAPI BRIDGE ———

@router.post("/webhook/telegram")
async def webhook(request: Request):
    update = Update.de_json(await request.json(), tg_app.bot)
    await tg_app.process_update(update)
    return {"ok": True}
