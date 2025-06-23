from fastapi import FastAPI
from app.telegram_adapter import router as tg_router, build_app

app = FastAPI()
app.include_router(tg_router)

tg_app = build_app()


@app.on_event("startup")
async def startup():
    await tg_app.initialize()

