import os
from fastapi import FastAPI, Request
from fastapi.responses import Response
from fastapi.middleware.cors import CORSMiddleware
from app.telegram_adapter import build_app

TOKEN = os.getenv("TELEGRAM_TOKEN")

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

tg_app = build_app(TOKEN)

@app.on_event("startup")
async def _init() -> None:
    await tg_app.initialize()

@app.post("/webhook/telegram")
async def webhook(req: Request) -> Response:
    await tg_app.process_update(await req.body())
    return Response(status_code=200)

@app.get("/")
def root() -> dict:
    return {"status": "ok"}

