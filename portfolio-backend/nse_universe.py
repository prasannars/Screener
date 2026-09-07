"""NSE listed-equity universe for All Stocks India.

Pulls the official EQUITY_L.csv (all NSE symbols) and overlays Nifty 500
industry names. Cached locally so the stock list is complete without
calling yfinance for every company.
"""
from __future__ import annotations

import csv
import io
import os
import time
from typing import Dict, List

import requests

from utils import get_logger, get_path

log = get_logger("nse")

EQUITY_URLS = (
    "https://nsearchives.nseindia.com/content/equities/EQUITY_L.csv",
    "https://archives.nseindia.com/content/equities/EQUITY_L.csv",
)
NIFTY500_URLS = (
    "https://nsearchives.nseindia.com/content/indices/ind_nifty500list.csv",
    "https://www.niftyindices.com/IndexConstituent/ind_nifty500list.csv",
)
CACHE_TTL_SEC = 24 * 60 * 60

_lock_cache: dict | None = None
_lock_loaded_at = 0.0


def _headers() -> dict:
    return {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
        "Accept": "text/csv,text/plain,*/*",
        "Referer": "https://www.nseindia.com/",
    }


def _session() -> requests.Session:
    session = requests.Session()
    session.trust_env = False
    session.headers.update(_headers())
    return session


def _download(urls: tuple[str, ...]) -> str:
    last_error = None
    session = _session()
    for url in urls:
        try:
            resp = session.get(url, timeout=30)
            resp.raise_for_status()
            text = resp.text
            if "Symbol" not in text[:200] and "SYMBOL" not in text[:200]:
                last_error = ValueError(f"{url} did not look like an NSE CSV")
                continue
            return text
        except Exception as exc:
            last_error = exc
            log.warning(f"NSE download failed from {url}: {exc}")
    raise last_error or ValueError("NSE list could not be downloaded")


def _cache_path(name: str) -> str:
    return get_path(f"data/nse/{name}")


def _load_or_download(name: str, urls: tuple[str, ...]) -> str:
    path = _cache_path(name)
    if os.path.exists(path) and (time.time() - os.path.getmtime(path)) < CACHE_TTL_SEC:
        with open(path, encoding="utf-8") as f:
            return f.read()
    text = _download(urls)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)
    return text


def _norm(row: dict) -> dict:
    return {(k or "").strip(): (v or "").strip() for k, v in row.items()}


def load_listed_equities() -> List[Dict]:
    """Return NSE EQ stocks: symbol, name, industry, series, isin."""
    global _lock_cache, _lock_loaded_at
    now = time.time()
    if _lock_cache is not None and now - _lock_loaded_at < CACHE_TTL_SEC:
        return _lock_cache

    try:
        equity_text = _load_or_download("equity_l.csv", EQUITY_URLS)
        nifty_text = _load_or_download("nifty500.csv", NIFTY500_URLS)
    except Exception as exc:
        log.warning(f"Using empty NSE universe ({exc})")
        if _lock_cache:
            return _lock_cache
        return []

    industry = {}
    for raw in csv.DictReader(io.StringIO(nifty_text)):
        row = _norm(raw)
        symbol = row.get("Symbol") or row.get("SYMBOL")
        if symbol:
            industry[symbol] = row.get("Industry") or ""

    stocks = []
    seen = set()
    for raw in csv.DictReader(io.StringIO(equity_text)):
        row = _norm(raw)
        symbol = row.get("SYMBOL") or row.get("Symbol")
        series = row.get("SERIES") or row.get("Series")
        if not symbol or series not in ("EQ", "BE") or symbol in seen:
            continue
        seen.add(symbol)
        stocks.append({
            "symbol": symbol,
            "name": row.get("NAME OF COMPANY") or symbol,
            "series": series,
            "isin": row.get("ISIN NUMBER") or row.get("ISIN") or None,
            "industry": industry.get(symbol) or None,
        })
    stocks.sort(key=lambda x: x["symbol"])
    log.info(f"Loaded {len(stocks)} NSE listed stocks")
    _lock_cache = stocks
    _lock_loaded_at = now
    return stocks
