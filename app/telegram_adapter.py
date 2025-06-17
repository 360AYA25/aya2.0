from fastapi import APIRouter, Request
from fastapi.responses import FileResponse
from telegram import Update
from telegram.ext import (
    Application, ContextTypes, AIORateLimiter,
    MessageHandler, CommandHandler, filters,
)
import os, openai, textwrap

from app.firestore_client import save_dialog, get_last_dialog
from app.state            import set_topic, get_topic

ROADMAP_FILE = "docs/roadmap/Aya Bot — Roadmap v0.3.pdf"

router = APIRouter()

TOKEN          = os.environ["TELEGRAM_TOKEN"]
openai.api_key = os.environ["OPENAI_KEY"]

tg_app = (
    Application.builder()
    .token(TOKEN)
    .rate_limiter(AIORateLimiter())
    .build()
)

# ───────────────────────── helpers ──────────────────────────
async def ask_gpt(user_id: str, prompt: str) -> str:
    topic   = await get_topic(user_id)
    history = await get_last_dialog(topic, limit=6)     # 🆕 берём 6 последних

    sys_msg = textwrap.dedent(f"""
        You are Aya — a helpful assistant.
        Current topic: {topic}.
        Conversation history (oldest → newest) is below, use it for context.
    """)

    ctx_msgs = []
    for m in history:
        ctx_msgs.append({"role": "user", "content": m["user"]})
        ctx_msgs.append({"role": "assistant", "content": m["bot"]})

    resp = await openai.ChatCompletion.acreate(
        model       = "gpt-4o-mini",
        temperature = 0.7,
        max_tokens  = 500,
        messages    = [{"role":"system","content":sys_msg}] + ctx_msgs +
                      [{"role":"user","content":prompt}]
    )
    return resp.choices[0].message.content.strip()
# ────────────────────────────────────────────────────────────

# ---------- /topic ------------------------------------------
async def cmd_topic(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not ctx.args:
        await update.message.reply_text("Usage: /topic <name>")
        return
    await set_topic(str(update.effective_user.id), ctx.args[0])
    await update.message.reply_text(f"✓ Topic switched to {ctx.args[0]}")

tg_app.add_handler(CommandHandler("topic", cmd_topic))

# ---------- /history ----------------------------------------
async def cmd_history(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    topic   = await get_topic(str(update.effective_user.id))
    history = await get_last_dialog(topic, 6)
    if not history:
        await update.message.reply_text("— empty —")
        return
    out = []
    for h in history:
        out.append(f"🧑 {h['user']}")
        out.append(f"🤖 {h['bot']}")
    await update.message.reply_text("\n".join(out))

tg_app.add_handler(CommandHandler("history", cmd_history))

# ---------- /echo (тест) ------------------------------------
async def cmd_echo(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not ctx.args:
        await update.message.reply_text("Usage: /echo <text>")
        return
    await update.message.reply_text(" ".join(ctx.args))

tg_app.add_handler(CommandHandler("echo", cmd_echo))

# ---------- обычный текст → GPT -----------------------------
async def gpt_reply(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return
    user_text = update.message.text.strip()
    user_id   = str(update.effective_user.id)

    bot_answer = await ask_gpt(user_id, user_text)
    await save_dialog(user_text, bot_answer, topic=await get_topic(user_id))
    await update.message.reply_text(bot_answer)

tg_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, gpt_reply))

# ---------- roadmap HTTP endpoint ---------------------------
@router.get("/roadmap/latest")
async def get_latest_roadmap():
    return FileResponse(ROADMAP_FILE)

# ---------- Telegram webhook --------------------------------
@router.post("/webhook/telegram")
async def telegram_webhook(req: Request):
    data   = await req.json()
    update = Update.de_json(data, tg_app.bot)
    await tg_app.initialize()
    await tg_app.process_update(update)
    return {"ok": True}

