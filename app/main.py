from fastapi import FastAPI
from app.telegram_adapter import router as tg_router

app = FastAPI()
app.include_router(tg_router)

@app.get("/healthz")
def health():
    return {"status": "ok"}
