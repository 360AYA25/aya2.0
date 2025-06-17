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
import os, openai

from app.firestore_client import save_dialog, get_last_dialog
from app.state import set_topic, get_topic

router = APIRouter()

TOKEN = os.environ["TELEGRAM_TOKEN"]
openai.api_key = os.environ["OPENAI_KEY"]

tg_app = (
    Application.builder()
    .token(TOKEN)
    .rate_limiter(AIORateLimiter())
    .build()
)

# ─────────── GPT ───────────
async def ask_gpt(user_id: str, prompt: str) -> str:
    resp = await openai.ChatCompletion.acreate(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": prompt},
        ],
        user=str(user_id),
        temperature=0.7,
        max_tokens=350,
    )
    return resp.choices[0].message.content.strip()
# ───────────────────────────

# /topic ----------------------------------------------------------
async def cmd_topic(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not ctx.args:
        await update.message.reply_text("Usage: /topic <name>")
        return
    topic = ctx.args[0]
    await set_topic(str(update.effective_user.id), topic)
    await update.message.reply_text(f"✓ Topic switched to {topic}")

# /history --------------------------------------------------------
async def cmd_history(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    topic = await get_topic(str(update.effective_user.id))
    history = await get_last_dialog(topic, limit=12)
    if not history:
        await update.message.reply_text("— empty —")
        return
    out = []
    for h in history:
        out.append(f"🧑 {h['user']}\n🤖 {h['bot']}")
    await update.message.reply_text("\n\n".join(out))

# /summary --------------------------------------------------------
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

# GPT reply -------------------------------------------------------
async def gpt_reply(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return
    user_text = update.message.text.strip()
    bot_answer = await ask_gpt(str(update.effective_user.id), user_text)
    topic = await get_topic(str(update.effective_user.id))
    await save_dialog(user_text, bot_answer, topic=topic)
    await update.message.reply_text(bot_answer)

# Handlers --------------------------------------------------------
tg_app.add_handler(CommandHandler("topic", cmd_topic))
tg_app.add_handler(CommandHandler("history", cmd_history))
tg_app.add_handler(CommandHandler("summary", cmd_summary))
tg_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, gpt_reply))

# Webhook endpoint -----------------------------------------------
@router.post("/webhook/telegram")
async def telegram_webhook(req: Request):
    data = await req.json()
    update = Update.de_json(data, tg_app.bot)
    await tg_app.initialize()
    await tg_app.process_update(update)
    return {"ok": True}

