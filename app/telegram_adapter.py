from fastapi import APIRouter, Request
from telegram import Update, Bot
from telegram.ext import (
    ApplicationBuilder, ContextTypes, AIORateLimiter,
    CommandHandler, MessageHandler, filters
)
import uuid
import os
from app.firestore_client import (
    save_dialog, get_dialog_page, get_dialog_total, set_topic, get_topic
)
from app.storage_client import put_file
from app.openai_client import ask_gpt
from app.doc_summarizer import summarize

router = APIRouter()
HISTORY_PAGE_SIZE = 10

@router.post("/webhook/telegram")
async def webhook(req: Request):
    update_json = await req.json()
    update = Update.de_json(update_json, req.app.state.tg_app.bot)
    await req.app.state.tg_app.process_update(update)
    return {"ok": True}

async def cmd_topic(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not ctx.args:
        if update.message:
            await update.message.reply_text("usage: /topic <name>")
        return
    if update.effective_user and update.message:
        await set_topic(str(update.effective_user.id), ctx.args[0])
        await update.message.reply_text("✓ Topic switched to " + ctx.args[0])

async def cmd_history(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if update.effective_user and update.message:
        uid = str(update.effective_user.id)
        try:
            page = int(ctx.args[0]) if ctx.args else 1
        except Exception:
            page = 1
        page = max(page, 1)
        size = HISTORY_PAGE_SIZE
        total = await get_dialog_total(uid)
        max_page = max((total + size - 1) // size, 1)
        page = min(page, max_page)
        msgs = await get_dialog_page(uid, page - 1, size)
        text = "\n\n".join(
            f"💬 {d['user']}\n🤖 {d['bot']}" for d in msgs
        ) or "— empty —"
        footer = f"\n\n◀️ {page} / {max_page} ▶️"
        await update.message.reply_text(text + footer)

async def cmd_upload(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.document:
        if update.message:
            await update.message.reply_text("Attach a file with /upload")
        return
    doc = update.message.document
    if ctx.bot:
        raw = await (await ctx.bot.get_file(doc.file_id)).download_as_bytearray()
        ext = os.path.splitext(doc.file_name)[1] if doc.file_name else ""
        name = f"{uuid.uuid4().hex}{ext}"
        url = await put_file(name, bytes(raw))
        await update.message.reply_text(f"✓ uploaded → {url}")

async def cmd_summarize(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.document:
        if update.message:
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
    summary = await summarize(bytes(raw), filename)
    await update.message.reply_text(summary, parse_mode="Markdown")

async def text_handler(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if update.effective_user and update.message and update.message.text:
        uid = str(update.effective_user.id)
        topic = await get_topic(uid) or "default"
        reply = await ask_gpt(update.message.text, topic)
        await save_dialog(uid, update.message.text, reply)
        await update.message.reply_text(reply)

async def build_app(token: str):
    app = (
        ApplicationBuilder()
        .token(token)
        .rate_limiter(AIORateLimiter())
        .build()
    )
    app.add_handler(CommandHandler("topic", cmd_topic))
    app.add_handler(CommandHandler("history", cmd_history))
    app.add_handler(CommandHandler("upload", cmd_upload))
    app.add_handler(CommandHandler("summarize", cmd_summarize))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_handler))
    return app

