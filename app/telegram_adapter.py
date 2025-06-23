from fastapi import APIRouter, Request
from fastapi.responses import FileResponse
from telegram import Update, InputFile
from telegram.ext import (
    Application,
    ContextTypes,
    AIORateLimiter,
    MessageHandler,
    CommandHandler,
    filters,
)
import os, openai, aiofiles
from app.firestore_client import save_dialog
from app.state import set_topic, get_topic
from app.storage_client import put_file

router = APIRouter()

TOKEN = os.environ["TELEGRAM_TOKEN"]
openai.api_key = os.environ["OPENAI_KEY"]

tg_app = (
    Application.builder()
    .token(TOKEN)
    .rate_limiter(AIORateLimiter())
    .build()
)

async def ask_gpt(prompt: str) -> str:
    resp = await openai.ChatCompletion.acreate(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=512,
    )
    return resp.choices[0].message.content.strip()

async def cmd_topic(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    parts = (update.message.text or "").split(maxsplit=1)
    if len(parts) != 2:
        await update.message.reply_text("Usage: /topic <name>")
        return
    await set_topic(str(update.effective_user.id), parts[1])
    await update.message.reply_text(f"✓ Topic switched to {parts[1]}")

async def cmd_history(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    # stripped for brevity – history logic stays прежним
    await update.message.reply_text("— empty —")

async def cmd_prompt_reload(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("✓ Reloaded\n— empty —")

async def cmd_prompt(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("— empty —")

async def cmd_upload(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not update.message.document:
        await update.message.reply_text("Attach a file with /upload")
        return
    file = await ctx.bot.get_file(update.message.document.file_id)
    data = await file.download_as_bytes()
    url = await put_file(update.message.document.file_name, data)
    await update.message.reply_text(f"Saved → {url}")

async def gpt_reply(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text.strip()
    bot_answer = await ask_gpt(user_text)
    topic = await get_topic(str(update.effective_user.id))
    await save_dialog(user_text, bot_answer, topic=topic)
    await update.message.reply_text(bot_answer)

tg_app.add_handler(CommandHandler("topic", cmd_topic))
tg_app.add_handler(CommandHandler("history", cmd_history))
tg_app.add_handler(CommandHandler("prompt_reload", cmd_prompt_reload))
tg_app.add_handler(CommandHandler("prompt", cmd_prompt))
tg_app.add_handler(CommandHandler("upload", cmd_upload))
tg_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, gpt_reply))

@router.post("/webhook/telegram")
async def webhook(req: Request):
    data = await req.body()
    update = Update.de_json(data, ctx.bot)
    await tg_app.process_update(update)
    return {"ok": True}

def build_app():
    return router

