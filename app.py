"""FastAPI dashboard for 2-day earnings-surprise returns."""

from __future__ import annotations

import threading
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from earnings_reaction.fetch import DEFAULT_TICKER
from earnings_reaction.pipeline import run_analysis

ROOT = Path(__file__).resolve().parent
STATIC_DIR = ROOT / "static"

app = FastAPI(title="Earnings surprise 2-day returns")
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

_cache: dict[str, dict] = {}
_lock = threading.Lock()


def _get_analysis(ticker: str, refresh: bool = False) -> dict:
    key = ticker.strip().upper() or DEFAULT_TICKER
    with _lock:
        if not refresh and key in _cache:
            return _cache[key]
    try:
        payload = run_analysis(key)
    except Exception as exc:  # noqa: BLE001 — surface Yahoo/network failures to the UI
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    with _lock:
        _cache[key] = payload
    return payload


@app.get("/")
def index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/api/health")
def health() -> dict:
    return {"ok": True}


@app.get("/api/analysis")
def analysis(
    ticker: str = Query(default=DEFAULT_TICKER, min_length=1, max_length=12),
    refresh: bool = Query(default=False),
) -> dict:
    if not ticker.replace("-", "").replace(".", "").isalnum():
        raise HTTPException(status_code=400, detail="Ticker must be alphanumeric.")
    return _get_analysis(ticker, refresh=refresh)
