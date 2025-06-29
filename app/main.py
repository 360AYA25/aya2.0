import os

# ===== DEBUG BLOCK (выведет инфу о секретах и переменных) =====
print("DEBUG: GOOGLE_APPLICATION_CREDENTIALS =", os.environ.get("GOOGLE_APPLICATION_CREDENTIALS"))
try:
    print("DEBUG: /etc/secrets/ =", os.listdir("/etc/secrets"))
except Exception as e:
    print("DEBUG: /etc/secrets/ error:", e)
# =============================================================

from fastapi import FastAPI
from app.telegram_adapter import router as tg_router, build_app

app = FastAPI()
app.include_router(tg_router)

@app.on_event("startup")
async def on_startup():
    app.state.tg_app = await build_app(os.environ["TELEGRAM_TOKEN"])
    await app.state.tg_app.initialize()

@app.on_event("shutdown")
async def on_shutdown():
    await app.state.tg_app.shutdown()

from core.prompt_loader import reload_prompts

@app.post("/reload_prompts")
async def reload_prompts_endpoint():
    reload_prompts()
    return {"reloaded": True}

@app.get("/ping")
async def ping():
    return {"pong": True}


