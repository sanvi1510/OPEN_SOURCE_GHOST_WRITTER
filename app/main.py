"""
FastAPI application entry point for Open-Source Ghostwriter.

Creates the FastAPI app, registers routes, configures logging,
and exposes a health-check endpoint.
"""

from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI

from app.webhook import router as webhook_router
from config import configure_logging


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    """Run startup / shutdown hooks."""
    configure_logging()
    yield


app = FastAPI(
    title="Open-Source Ghostwriter",
    description="Autonomous AI agent that detects and fixes outdated documentation.",
    version="1.0.0",
    lifespan=lifespan,
)

# ── Register sub-routers ────────────────────────────────────────────────
app.include_router(webhook_router)


@app.get("/", tags=["health"])
async def health_check() -> dict[str, str]:
    """Return a simple status payload to confirm the service is running."""
    return {"status": "ok"}
