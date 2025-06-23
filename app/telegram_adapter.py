from fastapi import APIRouter, Request
from telegram import Update
from telegram.ext import (
    Application,
    ContextTypes,
    AIORateLimiter,
    MessageHandler,
    CommandHandler,
    filters,
)

import os
import uuid
import openai

from app.firestore_client import save_dialog, get_dialog_page, set_topic
from app.storage_client import put_file
from app.file_reader import read_pdf, read_txt
from app.openai_client import ask_gpt  # helper that wraps OpenAI call

router = APIRouter()

TOKEN = os.environ["TELEGRAM_TOKEN"]
openai.api_key = os.environ["OPENAI_KEY"]


async def cmd_topic(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not ctx.args:
        await update.message.reply_text("usage: /topic <name>")
        return
    await set_topic(str(update.effective_user.id), ctx.args[0])
    await update.message.reply_text("✓ Topic switched to " + ctx.args[0])


async def cmd_history(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    rows = await get_dialog_page(str(update.effective_user.id), page=1, limit=20)
    if not rows:
        await update.message.reply_text("— empty —")
        return
    out = [f"💬 {r['user']}\n🤖 {r['bot']}" for r in rows]
    await update.message.reply_text("\n\n".join(out))


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
        await update.message.reply_text("Attach a PDF or TXT file with /summarize")
        return
    doc = update.message.document
    raw = await (await ctx.bot.get_file(doc.file_id)).download_as_bytearray()
    ext = os.path.splitext(doc.file_name)[1].lower()

    if ext == ".txt":
        text = read_txt(bytes(raw))
    elif ext == ".pdf":
        text = read_pdf(bytes(raw))
    else:
        await update.message.reply_text("Supported: .pdf .txt")
        return

    prompt = (
        "Give a concise 8-bullet summary of the following document:\n\n"
        + text[:16000]
    )
    summary = await ask_gpt(str(update.effective_user.id), prompt)
    await update.message.reply_text(summary)


async def cmd_ping(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Pong!")


def build_app() -> Application:
    app = (
        Application.builder()
        .token(TOKEN)
        .rate_limiter(AIORateLimiter())
        .build()
    )
    app.add_handler(CommandHandler("topic", cmd_topic))
    app.add_handler(CommandHandler("history", cmd_history))
    app.add_handler(CommandHandler("upload", cmd_upload))
    app.add_handler(CommandHandler("summarize", cmd_summarize))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, cmd_ping))
    return app


tg_app = build_app()


@router.post("/webhook/telegram")
async def webhook(request: Request):
    update = Update.de_json(await request.json(), tg_app.bot)
    await tg_app.process_update(update)
    return {"ok": True}

