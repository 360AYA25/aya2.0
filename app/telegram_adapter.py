from fastapi import APIRouter, Request
from telegram import Update
from telegram.ext import (
    Application, ContextTypes, AIORateLimiter,
    MessageHandler, CommandHandler, filters,
)
import os, openai, asyncio

from app.firestore_client import save_dialog
from app.state           import set_topic, get_topic
from app.storage_client import put_file

router = APIRouter()

TOKEN         = os.environ["TELEGRAM_TOKEN"]
openai.api_key= os.environ["OPENAI_KEY"]

tg_app = (
    Application.builder()
    .token(TOKEN)
    .rate_limiter(AIORateLimiter())
    .build()
)

# -------- GPT helper -------------------------------------------------
async def ask_gpt(user_id: str, prompt: str) -> str:
    resp = await openai.ChatCompletion.acreate(
        model="gpt-4o-mini",
        messages=[{"role":"user","content":prompt}],
        temperature=0.7, max_tokens=500,
        user=user_id,
    )
    return resp.choices[0].message.content.strip()
# --------------------------------------------------------------------


async def cmd_topic(update:Update, ctx:ContextTypes.DEFAULT_TYPE):
    if not ctx.args:
        await update.message.reply_text("Usage: /topic <name>")
        return
    topic = ctx.args[0]
    await set_topic(str(update.effective_user.id), topic)
    await update.message.reply_text(f"✓ Topic switched to {topic}")


async def cmd_history(update:Update, ctx:ContextTypes.DEFAULT_TYPE):
    topic = await get_topic(str(update.effective_user.id))
    history = await get_last_dialog(topic, limit=12)
    if not history:
        await update.message.reply_text("— empty —")
        return
    lines=[]
    for h in history:
        lines.append(f"🧑 {h['user']}\n🤖 {h['bot']}")
    await update.message.reply_text("\n\n".join(lines))


async def cmd_summary(update:Update, ctx:ContextTypes.DEFAULT_TYPE):
    topic   = await get_topic(str(update.effective_user.id))
    history = await get_last_dialog(topic, limit=12)
    if not history:
        await update.message.reply_text("— empty —")
        return
    convo=[]
    for h in history:
        convo.append(f"User: {h['user']}\nBot: {h['bot']}")
    prompt = "Summarize the following conversation in 5 bullet points:\n\n" + "\n\n".join(convo)
    summary = await ask_gpt(str(update.effective_user.id), prompt)
    await update.message.reply_text(summary)


async def cmd_upload(update:Update, ctx:ContextTypes.DEFAULT_TYPE):
    doc = update.message.document
    if not doc:
        await update.message.reply_text("Attach a file with /upload")
        return
    file   = await doc.get_file()
    data   = await file.download_as_bytearray()
    url    = put_file(doc.file_name, data)
    await update.message.reply_text(f"✅ Saved: {url}")


async def gpt_reply(update:Update, ctx:ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return
    user_text = update.message.text.strip()
    user_id   = str(update.effective_user.id)
    bot_ans   = await ask_gpt(user_id, user_text)
    topic     = await get_topic(user_id)
    await save_dialog(user_text, bot_ans, topic=topic)
    await update.message.reply_text(bot_ans)


tg_app.add_handler(CommandHandler("topic",    cmd_topic))
tg_app.add_handler(CommandHandler("history",  cmd_history))
tg_app.add_handler(CommandHandler("summary",  cmd_summary))
tg_app.add_handler(CommandHandler("upload",   cmd_upload))
tg_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, gpt_reply))


# ---------------- webhook ---------------------------------------------------
@router.post("/webhook/telegram")
async def telegram_webhook(req: Request):
    data = await req.json()
    update = Update.de_json(data, tg_app.bot)
    await tg_app.initialize()
    await tg_app.process_update(update)
    return {"ok": True}

