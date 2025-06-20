import os
import pathlib
import mimetypes
import aiofiles
import openai

from fastapi import APIRouter, Request
from fastapi.responses import FileResponse
from fastapi.exceptions import HTTPException

from telegram import Update
from telegram.ext import (
    Application,
    ContextTypes,
    AIORateLimiter,
    CommandHandler,
    MessageHandler,
    filters,
)

from app.firestore_client import save_dialog, get_last_dialog
from app.state import set_topic, get_topic

# ────────── TELEGRAM APP ──────────
router = APIRouter()
TOKEN = os.environ["TELEGRAM_TOKEN"]
openai.api_key = os.environ["OPENAI_KEY"]

tg_app = (
    Application.builder()
    .token(TOKEN)
    .rate_limiter(AIORateLimiter())
    .build()
)

# ────────── GPT HELPER ──────────
async def ask_gpt(user_id: str, prompt: str) -> str:
    resp = await openai.ChatCompletion.acreate(
        model="gpt-3.5-turbo",
        user=user_id,
        messages=[{"role": "user", "content": prompt}],
    )
    return resp.choices[0].message.content.strip()

# ────────── CMD /topic ──────────
async def cmd_topic(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return
    parts = update.message.text.split(maxsplit=1)
    if len(parts) != 2:
        await update.message.reply_text("Usage: /topic <name>")
        return
    topic = parts[1].strip()
    await set_topic(str(update.effective_user.id), topic)
    await update.message.reply_text(f"✓ Topic switched to {topic}")

# ────────── CMD /history ──────────
async def cmd_history(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    topic = await get_topic(str(update.effective_user.id))
    history = await get_last_dialog(topic)
    if not history:
        await update.message.reply_text("— empty —")
        return
    lines = []
    for h in history:
        lines.append(f"👤 {h['user']}\n🤖 {h['bot']}")
    await update.message.reply_text("\n\n".join(lines))

# ────────── CMD /summary ──────────
async def cmd_summary(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    topic = await get_topic(str(update.effective_user.id))
    history = await get_last_dialog(topic, limit=12)
    if not history:
        await update.message.reply_text("— empty —")
        return
    convo = []
    for h in history:
        convo.append(f"User: {h['user']}\nBot: {h['bot']}")
    summary_prompt = (
        "Summarize the following conversation in 5 bullet points:\n\n"
        + "\n\n".join(convo)
    )
    summary = await ask_gpt(str(update.effective_user.id), summary_prompt)
    await update.message.reply_text(summary)

# ────────── CMD /prompt & /prompt_reload ──────────
_SYSTEM_PROMPT_PATH = pathlib.Path("system_prompt.txt")

async def cmd_prompt(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not _SYSTEM_PROMPT_PATH.exists():
        await update.message.reply_text("— empty —")
        return
    await update.message.reply_document(_SYSTEM_PROMPT_PATH.open("rb"))

async def cmd_prompt_reload(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("✓ Reloaded")
    # логика обновления промпта (если будет нужна) добавится позже

# ────────── CMD /upload (LOCAL) ──────────
UPLOAD_DIR = pathlib.Path("local_uploads")
UPLOAD_DIR.mkdir(exist_ok=True)

async def cmd_upload(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    if not (msg and msg.document):
        return
    if not (msg.caption and msg.caption.lstrip().startswith("/upload")):
        return

    telegram_file = await msg.document.get_file()
    filename = msg.document.file_name or telegram_file.file_id
    dst = UPLOAD_DIR / filename
    await telegram_file.download_to_drive(custom_path=str(dst))
    await msg.reply_text(f"✅ saved → /files/{filename}")

# ────────── GPT REPLY (default) ──────────
async def gpt_reply(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return
    user_text = update.message.text.strip()
    bot_answer = await ask_gpt(str(update.effective_user.id), user_text)
    topic = await get_topic(str(update.effective_user.id))
    await save_dialog(user_text, bot_answer, topic=topic)
    await update.message.reply_text(bot_answer)

# ────────── ROUTES & HANDLERS ──────────
ROADMAP_FILE = "docs/roadmap/Aya Bot — Roadmap v0.3.pdf"

@router.get("/roadmap/latest")
async def get_latest_roadmap():
    if not pathlib.Path(ROADMAP_FILE).exists():
        raise HTTPException(status_code=404)
    return FileResponse(ROADMAP_FILE, media_type="application/pdf")

@router.post("/webhook/telegram")
async def webhook(request: Request):
    data = await request.json()
    update = Update.de_json(data, tg_app.bot)
    await tg_app.process_update(update)
    return {"ok": True}

tg_app.add_handler(CommandHandler("topic", cmd_topic))
tg_app.add_handler(CommandHandler("history", cmd_history))
tg_app.add_handler(CommandHandler("summary", cmd_summary))
tg_app.add_handler(CommandHandler("prompt", cmd_prompt))
tg_app.add_handler(CommandHandler("prompt_reload", cmd_prompt_reload))
tg_app.add_handler(MessageHandler(filters.Document.ALL, cmd_upload))
tg_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, gpt_reply))

