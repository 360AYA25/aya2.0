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
import os, openai, uuid, mimetypes, asyncio
from app.firestore_client import (
    save_dialog,
    get_topic,
    set_topic,
    get_dialog_page,
)
from app.storage_client import put_file

router = APIRouter()

openai.api_key = os.environ["OPENAI_KEY"]
TOKEN = os.environ["TELEGRAM_TOKEN"]

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
        temperature=0.7,
    )
    return resp.choices[0].message.content.strip()


async def cmd_topic(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not ctx.args:
        await update.message.reply_text("usage: /topic <name>")
        return
    await set_topic(str(update.effective_user.id), ctx.args[0])
    await update.message.reply_text("✓ Topic switched to " + ctx.args[0])


async def cmd_history(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    page = int(ctx.args[0]) if ctx.args else 1
    topic = await get_topic(str(update.effective_user.id))
    history = await get_dialog_page(topic, limit=6, page=page)
    if not history:
        await update.message.reply_text("— empty —")
        return
    out = []
    for h in history:
        out.append(f"💬 {h['user']}\n🤖 {h['bot']}")
    await update.message.reply_text("\n\n".join(out))


async def cmd_upload(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.document:
        await update.message.reply_text("Attach a file with /upload")
        return
    doc = update.message.document
    tg_file = await ctx.bot.get_file(doc.file_id)
    raw = await tg_file.download_as_bytearray()
    ext = os.path.splitext(doc.file_name)[1]
    name = f"{uuid.uuid4().hex}{ext}"
    url = await put_file(name, bytes(raw))
    await update.message.reply_text(f"✓ uploaded → {url}")


async def gpt_reply(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return
    user_text = update.message.text.strip()
    topic = await get_topic(str(update.effective_user.id))
    bot_answer = await ask_gpt(user_text)
    await save_dialog(user_text, bot_answer, topic=topic)
    await update.message.reply_text(bot_answer)


tg_app.add_handler(CommandHandler("topic", cmd_topic))
tg_app.add_handler(CommandHandler("history", cmd_history))
tg_app.add_handler(CommandHandler("upload", cmd_upload))
tg_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, gpt_reply))


@router.post("/webhook/telegram")
async def telegram_webhook(req: Request):
    data = await req.json()
    update = Update.de_json(data, tg_app.bot)
    await tg_app.process_update(update)
    return {"ok": True}


def build_app():
    return tg_app

