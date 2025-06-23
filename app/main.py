from fastapi import FastAPI
from app.telegram_adapter import router as tg_router, build_app
import os

app = FastAPI()
app.include_router(tg_router)

@app.on_event("startup")
async def on_startup():
    app.state.tg_app = await build_app(os.environ["TELEGRAM_TOKEN"])
    await app.state.tg_app.initialize()

@app.on_event("shutdown")
async def on_shutdown():
    await app.state.tg_app.shutdown()

