from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import auth, orders, products, shipments, tracking, webhooks
from app.core.config import get_settings
from app.db import SessionLocal, init_db
from app.services.seed import seed_defaults

settings = get_settings()
app = FastAPI(title=settings.app_name)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup() -> None:
    init_db()
    db = SessionLocal()
    try:
        seed_defaults(db)
    finally:
        db.close()


@app.get("/health")
def health():
    return {"status": "ok"}


app.include_router(auth.router, prefix=settings.api_prefix)
app.include_router(products.router, prefix=settings.api_prefix)
app.include_router(orders.router, prefix=settings.api_prefix)
app.include_router(shipments.router, prefix=settings.api_prefix)
app.include_router(tracking.router, prefix=settings.api_prefix)
app.include_router(webhooks.router, prefix=settings.api_prefix)
