from telegram import Update
from telegram.ext import (
    Application, ContextTypes, AIORateLimiter,
    CommandHandler, MessageHandler, filters
)

import uuid
import os

from app.firestore_client import (
    save_dialog, get_dialog_page, set_topic, get_topic
)
from app.storage_client import put_file
from app.openai_client import ask_gpt

async def cmd_topic(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not ctx.args:
        await update.message.reply_text("usage: /topic <name>")
        return
    await set_topic(str(update.effective_user.id), ctx.args[0])
    await update.message.reply_text("✓ Topic switched to " + ctx.args[0])

async def cmd_history(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = str(update.effective_user.id)
    page = await get_dialog_page(uid, 0)
    txt = "\n\n".join(f"💬 {d['user']}\n🤖 {d['bot']}" for d in page) or "— empty —"
    await update.message.reply_text(txt)

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

async def text_handler(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = str(update.effective_user.id)
    topic = await get_topic(uid) or "default"
    reply = await ask_gpt(update.message.text, topic)
    await save_dialog(uid, update.message.text, reply)
    await update.message.reply_text(reply)

async def build_app(token: str):
    app = (
        Application.builder()
        .token(token)
        .rate_limiter(AIORateLimiter())
        .build()
    )
    app.add_handler(CommandHandler("topic", cmd_topic))
    app.add_handler(CommandHandler("history", cmd_history))
    app.add_handler(CommandHandler("upload", cmd_upload))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_handler))
    return app

