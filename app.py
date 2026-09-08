"""FastAPI dashboard for 2-day earnings-surprise returns."""

from __future__ import annotations

import threading
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from earnings_reaction.additions import run_sp500_additions
from earnings_reaction.corrections import run_corrections
from earnings_reaction.fetch import DEFAULT_TICKER
from earnings_reaction.indexes_ytd import run_index_ytd
from earnings_reaction.pipeline import run_analysis

ROOT = Path(__file__).resolve().parent
STATIC_DIR = ROOT / "static"

app = FastAPI(title="Question 4. AMZN 2-day earnings surprises")
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

_cache: dict[str, dict] = {}
_corrections_cache: dict | None = None
_ytd_cache: dict | None = None
_additions_cache: dict | None = None
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


@app.get("/question4")
def question4_page() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/corrections")
def corrections_page() -> FileResponse:
    return FileResponse(STATIC_DIR / "corrections.html")


@app.get("/indexes-ytd")
def indexes_ytd_page() -> FileResponse:
    return FileResponse(STATIC_DIR / "indexes.html")


@app.get("/additions")
def additions_page() -> FileResponse:
    return FileResponse(STATIC_DIR / "additions.html")


@app.get("/api/health")
def health() -> dict:
    return {"ok": True}


@app.get("/api/corrections")
def corrections(refresh: bool = Query(default=False)) -> dict:
    global _corrections_cache
    with _lock:
        if not refresh and _corrections_cache is not None:
            return _corrections_cache
    try:
        payload = run_corrections()
    except Exception as exc:  # noqa: BLE001 — surface Yahoo/network failures to the UI
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    with _lock:
        _corrections_cache = payload
    return payload


@app.get("/api/indexes-ytd")
def indexes_ytd(refresh: bool = Query(default=False)) -> dict:
    global _ytd_cache
    with _lock:
        if not refresh and _ytd_cache is not None:
            return _ytd_cache
    try:
        payload = run_index_ytd()
    except Exception as exc:  # noqa: BLE001 — surface Yahoo/network failures to the UI
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    with _lock:
        _ytd_cache = payload
    return payload


@app.get("/api/additions")
def additions(refresh: bool = Query(default=False)) -> dict:
    global _additions_cache
    with _lock:
        if not refresh and _additions_cache is not None:
            return _additions_cache
    try:
        payload = run_sp500_additions()
    except Exception as exc:  # noqa: BLE001 — surface Wikipedia/network failures to the UI
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    with _lock:
        _additions_cache = payload
    return payload


@app.get("/api/analysis")
def analysis(
    ticker: str = Query(default=DEFAULT_TICKER, min_length=1, max_length=12),
    refresh: bool = Query(default=False),
) -> dict:
    if not ticker.replace("-", "").replace(".", "").isalnum():
        raise HTTPException(status_code=400, detail="Ticker must be alphanumeric.")
    return _get_analysis(ticker, refresh=refresh)
