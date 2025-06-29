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
from app.search_client import search

router = APIRouter()
HISTORY_PAGE_SIZE = 10
UPLOAD_LIMIT = 10 * 1024 * 1024
ALLOWED_EXTS = (".pdf", ".txt", ".md")

@router.post("/webhook/telegram")
async def webhook(req: Request):
    try:
        update_json = await req.json()
        update = Update.de_json(update_json, req.app.state.tg_app.bot)
        await req.app.state.tg_app.process_update(update)
        return {"ok": True}
    except Exception as e:
        import traceback
        tb = traceback.format_exc()
        print(f"[ERROR webhook] {e}\n{tb}")
        return {"ok": False, "error": str(e), "traceback": tb}

async def cmd_topic(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    try:
        if not ctx.args:
            if update.message:
                await update.message.reply_text("usage: /topic <name>")
            return
        if update.effective_user and update.message:
            await set_topic(str(update.effective_user.id), ctx.args[0])
            await update.message.reply_text("✓ Topic switched to " + ctx.args[0])
    except Exception as e:
        import traceback
        tb = traceback.format_exc()
        if update.message:
            await update.message.reply_text(f"❗️Ошибка topic: {e}\n```{tb}```")
        print(f"[ERROR topic] {e}\n{tb}")

async def cmd_history(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    try:
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
    except Exception as e:
        import traceback
        tb = traceback.format_exc()
        if update.message:
            await update.message.reply_text(f"❗️Ошибка history: {e}\n```{tb}```")
        print(f"[ERROR history] {e}\n{tb}")

async def cmd_upload(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    try:
        if not update.message or not update.message.document:
            if update.message:
                await update.message.reply_text("Attach a .pdf, .txt, or .md file with /upload")
            return
        doc = update.message.document
        ext = os.path.splitext(doc.file_name or "")[1].lower()
        if ext not in ALLOWED_EXTS:
            if update.message:
                await update.message.reply_text(f"🚫 Unsupported file type ({ext})")
            logging.warning(f"Unsupported file type: {ext}")
            return
        file_size = doc.file_size if doc.file_size is not None else 0
        if file_size > UPLOAD_LIMIT:
            if update.message:
                await update.message.reply_text("🚫 File too large (>10 MB)")
            logging.warning(f"File too large: {file_size} bytes")
            return 
        if ctx.bot:
            raw = await (await ctx.bot.get_file(doc.file_id)).download_as_bytearray()
            name = f"{uuid.uuid4().hex}{ext}"
            url = await put_file(name, bytes(raw))
            await update.message.reply_text(f"✓ uploaded → {url}")
    except Exception as e:
        import traceback
        tb = traceback.format_exc()
        if update.message:
            await update.message.reply_text(f"❗️Ошибка upload: {e}\n```{tb}```")
        print(f"[ERROR upload] {e}\n{tb}")

async def cmd_search(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    try:
        if not ctx.args:
            if update.message:
                await update.message.reply_text("usage: /search <query>")
            return
        query = " ".join(ctx.args)
        if len(query) > 256:
            if update.message:
                await update.message.reply_text("Query too long (≤ 256 chars)")
            return
        hits = await search(query)
        if not hits:
            if update.message:
                await update.message.reply_text("— no matches —")
            return
        context = "\n\n".join(h["text"][:2000] for h in hits)
        answer = await ask_gpt(query, context)
        links = "\n".join(f"• {h['title']} — {h['url']}" for h in hits)
        if update.message:
            await update.message.reply_text(f"{answer}\n\n{links}")
    except Exception as e:
        import traceback
        tb = traceback.format_exc()
        if update.message:
            await update.message.reply_text(f"❗️Ошибка search: {e}\n```{tb}```")
        print(f"[ERROR search] {e}\n{tb}")

async def cmd_summarize(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    try:
        if not update.message or not update.message.document:
            if update.message:
                await update.message.reply_text("Attach a .pdf, .txt или .md файл с /summarize")
            return
        doc = update.message.document
        filename = doc.file_name or "document"
        if not filename.lower().endswith((".pdf", ".txt", ".md")):
            if update.message:
                await update.message.reply_text("Поддерживаются только PDF, TXT, MD (до 10 кБ)")
            return
        raw = await (await ctx.bot.get_file(doc.file_id)).download_as_bytearray()
        if len(raw) > 10_000:
            if update.message:
                await update.message.reply_text("Файл слишком большой (до 10 кБ)")
            return
        summary = await summarize(bytes(raw), filename)
        if not summary or not summary.strip():
            if update.message:
                await update.message.reply_text("Summary пустое или не удалось сгенерировать.")
        else:
            if update.message:
                await update.message.reply_text(summary, parse_mode="Markdown")
    except Exception as e:
        import traceback
        tb = traceback.format_exc()
        if update.message:
            await update.message.reply_text(f"❗️Ошибка summarize: {e}\n```{tb}```")
        print(f"[ERROR summarize] {e}\n{tb}")

async def text_handler(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    try:
        if update.effective_user and update.message and update.message.text:
            uid = str(update.effective_user.id)
            topic = await get_topic(uid) or "default"
            reply = await ask_gpt(update.message.text, topic)
            await save_dialog(uid, update.message.text, reply)
            await update.message.reply_text(reply)
    except Exception as e:
        import traceback
        tb = traceback.format_exc()
        if update.message:
            await update.message.reply_text(f"❗️Ошибка text_handler: {e}\n```{tb}```")
        print(f"[ERROR text_handler] {e}\n{tb}")

async def build_app(token: str):
    app = (
        ApplicationBuilder()
        .token(token)
        .rate_limiter(AIORateLimiter())
        .build()
    )
    app.add_handler(CommandHandler("topic", cmd_topic))
    app.add_handler(CommandHandler("history", cmd_history))
    app.add_handler(MessageHandler(filters.Document.ALL & filters.CaptionRegex(r"^/upload"), cmd_upload))
    app.add_handler(CommandHandler("search", cmd_search))
    app.add_handler(CommandHandler("summarize", cmd_summarize))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_handler))
    return app
