import os, openai
from fastapi import APIRouter, Request
from telegram import Update
from telegram.ext import (
    Application, ContextTypes, AIORateLimiter,
    MessageHandler, CommandHandler, filters,
)

from app.firestore_client import (
    save_dialog, get_last_dialog,
    get_prompt, set_prompt, reload_prompt,
)
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

# ─────────── GPT helper ───────────
async def ask_gpt(user_id: str, prompt: str) -> str:
    topic = await get_topic(user_id)
    sys_prompt = await get_prompt(topic) or "You are AYA bot."
    history = await get_last_dialog(topic, 6)

    messages = [{"role": "system", "content": sys_prompt}]
    for h in history:
        messages.append({"role": "user", "content": h["user"]})
        messages.append({"role": "assistant", "content": h["bot"]})
    messages.append({"role": "user", "content": prompt})

    resp = await openai.ChatCompletion.acreate(
        model="gpt-4o-mini",
        messages=messages,
        user=user_id,
        temperature=0.7,
        max_tokens=500,
    )
    return resp.choices[0].message.content.strip()

# ─────────── commands ───────────
async def cmd_topic(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not ctx.args:
        await update.message.reply_text("Usage: /topic <name>")
        return
    await set_topic(str(update.effective_user.id), ctx.args[0])
    await update.message.reply_text(f"✓ Topic switched to {ctx.args[0]}")

async def cmd_history(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    topic = await get_topic(str(update.effective_user.id))
    history = await get_last_dialog(topic, 12)
    if not history:
        await update.message.reply_text("— empty —")
        return
    await update.message.reply_text(
        "\n\n".join(f"👤 {h['user']}\n🤖 {h['bot']}" for h in history)
    )

async def cmd_prompt(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    topic = await get_topic(str(update.effective_user.id))
    if not ctx.args:
        cur = await get_prompt(topic) or "— empty —"
        await update.message.reply_text(cur)
        return
    await set_prompt(topic, " ".join(ctx.args))
    await update.message.reply_text("✓ Prompt saved")

async def cmd_prompt_reload(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    topic = await get_topic(str(update.effective_user.id))
    text = await reload_prompt(topic) or "— empty —"
    await update.message.reply_text(f"✓ Reloaded\n{text}")

async def gpt_reply(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return
    user_text = update.message.text.strip()
    user_id = str(update.effective_user.id)
    bot_text = await ask_gpt(user_id, user_text)
    topic = await get_topic(user_id)
    await save_dialog(user_text, bot_text, topic=topic)
    await update.message.reply_text(bot_text)

# ─────────── handlers ───────────
tg_app.add_handler(CommandHandler("topic",          cmd_topic))
tg_app.add_handler(CommandHandler("history",        cmd_history))
tg_app.add_handler(CommandHandler("prompt",         cmd_prompt))
tg_app.add_handler(CommandHandler("prompt_reload",  cmd_prompt_reload))
tg_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, gpt_reply))

# ─────────── webhook ───────────
@router.post("/webhook/telegram")
async def telegram_webhook(req: Request):
    data = await req.json()
    update = Update.de_json(data, tg_app.bot)
    await tg_app.initialize()
    await tg_app.process_update(update)
    return {"ok": True}

@router.get("/health")
async def health():
    return {"status": "ok"}

