"""
Stock fundamental metrics and scoring.
Calculates quality scores based on P/E, P/B, ROE, ROA, debt ratios, etc.
"""
from __future__ import annotations

import json
import os
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, Optional

_FUND_CACHE: dict[str, tuple[float, dict]] = {}
_CACHE_TTL_SEC = 24 * 60 * 60
_disk_loaded = False
_disk_lock = threading.Lock()
_warming = False


def _disk_path() -> str:
    from utils import get_path
    return get_path("data/nse/fundamentals.json")


def _load_disk_cache():
    global _disk_loaded
    if _disk_loaded:
        return
    with _disk_lock:
        if _disk_loaded:
            return
        path = _disk_path()
        if os.path.exists(path):
            try:
                with open(path, encoding="utf-8") as f:
                    payload = json.load(f)
                for symbol, entry in (payload or {}).items():
                    if not isinstance(entry, dict):
                        continue
                    ts = float(entry.get("_ts") or 0)
                    row = {k: v for k, v in entry.items() if k != "_ts"}
                    _FUND_CACHE[symbol] = (ts, row)
            except (OSError, json.JSONDecodeError, TypeError, ValueError):
                pass
        _disk_loaded = True


def _save_disk_cache():
    path = _disk_path()
    payload = {}
    with _disk_lock:
        for symbol, (ts, row) in _FUND_CACHE.items():
            payload[symbol] = {**row, "_ts": ts}
        with open(path, "w", encoding="utf-8") as f:
            json.dump(payload, f)

def _to_float(value):
    """Coerce Yahoo/JSON values to float. Strings like 'N/A' become None."""
    if value is None or value == "":
        return None
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        if value != value:  # NaN
            return None
        return float(value)
    try:
        text = str(value).strip().replace(",", "")
        if not text or text.upper() in {"N/A", "NA", "NONE", "NULL", "-", "NAN", "INF", "-INF"}:
            return None
        number = float(text)
        if number != number:
            return None
        return number
    except (TypeError, ValueError):
        return None


def calculate_stock_score(fundamentals: Dict) -> Dict:
    """
    Calculate a 0-100 fundamental score for a stock.
    Returns: {score, grade, reasons}
    """
    score = 50  # Base score
    reasons = []
    
    pe = _to_float(fundamentals.get('pe_ratio'))
    pb = _to_float(fundamentals.get('pb_ratio'))
    roe = _to_float(fundamentals.get('roe'))
    roa = _to_float(fundamentals.get('roa'))
    debt_to_equity = _to_float(fundamentals.get('debt_to_equity'))
    current_ratio = _to_float(fundamentals.get('current_ratio'))
    profit_margin = _to_float(fundamentals.get('profit_margin'))
    revenue_growth = _to_float(fundamentals.get('revenue_growth'))
    dividend_yield = _to_float(fundamentals.get('dividend_yield'))
    
    # P/E Ratio scoring (lower is better, but not too low)
    if pe is not None:
        if pe < 0:
            score -= 15
            reasons.append("Negative P/E (loss-making)")
        elif pe < 15:
            score += 15
            reasons.append(f"Low P/E ({pe:.1f}) - potentially undervalued")
        elif pe < 25:
            score += 5
            reasons.append(f"Reasonable P/E ({pe:.1f})")
        elif pe < 40:
            score -= 5
            reasons.append(f"High P/E ({pe:.1f})")
        else:
            score -= 15
            reasons.append(f"Very high P/E ({pe:.1f}) - potentially overvalued")
    
    # P/B Ratio scoring
    if pb is not None:
        if pb < 1:
            score += 10
            reasons.append(f"Low P/B ({pb:.2f}) - trading below book value")
        elif pb < 3:
            score += 5
            reasons.append(f"Reasonable P/B ({pb:.2f})")
        elif pb < 5:
            score -= 5
            reasons.append(f"High P/B ({pb:.2f})")
        else:
            score -= 10
            reasons.append(f"Very high P/B ({pb:.2f})")
    
    # ROE scoring (higher is better)
    if roe is not None:
        roe_pct = roe * 100 if roe < 1 else roe
        if roe_pct > 20:
            score += 15
            reasons.append(f"Excellent ROE ({roe_pct:.1f}%)")
        elif roe_pct > 15:
            score += 10
            reasons.append(f"Good ROE ({roe_pct:.1f}%)")
        elif roe_pct > 10:
            score += 5
            reasons.append(f"Average ROE ({roe_pct:.1f}%)")
        elif roe_pct > 0:
            score -= 5
            reasons.append(f"Low ROE ({roe_pct:.1f}%)")
        else:
            score -= 15
            reasons.append(f"Negative ROE ({roe_pct:.1f}%)")
    
    # ROA scoring
    if roa is not None:
        roa_pct = roa * 100 if roa < 1 else roa
        if roa_pct > 10:
            score += 10
            reasons.append(f"Excellent ROA ({roa_pct:.1f}%)")
        elif roa_pct > 5:
            score += 5
            reasons.append(f"Good ROA ({roa_pct:.1f}%)")
        elif roa_pct < 0:
            score -= 10
            reasons.append(f"Negative ROA ({roa_pct:.1f}%)")
    
    # Debt-to-Equity scoring (lower is better)
    if debt_to_equity is not None:
        if debt_to_equity < 50:
            score += 10
            reasons.append(f"Low debt (D/E: {debt_to_equity:.1f}%)")
        elif debt_to_equity < 100:
            score += 5
            reasons.append(f"Moderate debt (D/E: {debt_to_equity:.1f}%)")
        elif debt_to_equity < 200:
            score -= 5
            reasons.append(f"High debt (D/E: {debt_to_equity:.1f}%)")
        else:
            score -= 15
            reasons.append(f"Very high debt (D/E: {debt_to_equity:.1f}%)")
    
    # Current ratio (liquidity)
    if current_ratio is not None:
        if current_ratio > 2:
            score += 5
            reasons.append(f"Strong liquidity (Current ratio: {current_ratio:.2f})")
        elif current_ratio > 1:
            score += 2
        else:
            score -= 5
            reasons.append(f"Weak liquidity (Current ratio: {current_ratio:.2f})")
    
    # Profit margin
    if profit_margin is not None:
        margin_pct = profit_margin * 100 if profit_margin < 1 else profit_margin
        if margin_pct > 20:
            score += 10
            reasons.append(f"High profit margin ({margin_pct:.1f}%)")
        elif margin_pct > 10:
            score += 5
        elif margin_pct < 0:
            score -= 10
            reasons.append(f"Negative profit margin ({margin_pct:.1f}%)")
    
    # Revenue growth
    if revenue_growth is not None:
        growth_pct = revenue_growth * 100 if revenue_growth < 1 else revenue_growth
        if growth_pct > 20:
            score += 10
            reasons.append(f"Strong revenue growth ({growth_pct:.1f}%)")
        elif growth_pct > 10:
            score += 5
        elif growth_pct < 0:
            score -= 5
            reasons.append(f"Declining revenue ({growth_pct:.1f}%)")
    
    # Dividend yield
    if dividend_yield is not None:
        yield_pct = dividend_yield * 100 if dividend_yield < 1 else dividend_yield
        if yield_pct > 3:
            score += 5
            reasons.append(f"Good dividend yield ({yield_pct:.2f}%)")
        elif yield_pct > 1:
            score += 2
    
    # Cap score between 0-100
    score = max(0, min(100, score))
    
    # Determine grade
    if score >= 80:
        grade = 'A'
    elif score >= 65:
        grade = 'B'
    elif score >= 50:
        grade = 'C'
    elif score >= 35:
        grade = 'D'
    else:
        grade = 'F'
    
    return {
        'score': round(score, 1),
        'grade': grade,
        'reasons': reasons[:5]  # Top 5 reasons
    }

def get_cached_fundamentals(symbol: str) -> Dict:
    """Return cached fundamentals without hitting the network."""
    _load_disk_cache()
    cached = _FUND_CACHE.get(symbol)
    if cached:
        return dict(cached[1])
    return {}


def get_fundamentals(symbol: str) -> Dict:
    """
    Fetch fundamentals for a single stock symbol.
    Wrapper around yfinance for convenience. Results are cached on disk.
    """
    _load_disk_cache()
    now = time.time()
    cached = _FUND_CACHE.get(symbol)
    if cached and now - cached[0] < _CACHE_TTL_SEC and cached[1].get("current_price"):
        return dict(cached[1])

    import yfinance as yf

    try:
        yf_symbol = f"{symbol}.NS"
        ticker = yf.Ticker(yf_symbol)
        info = ticker.info or {}

        if not info or info.get("regularMarketPrice") is None:
            yf_symbol = f"{symbol}.BO"
            ticker = yf.Ticker(yf_symbol)
            info = ticker.info or {}

        result = {
            "symbol": symbol,
            "name": info.get("shortName") or info.get("longName") or symbol,
            "current_price": _to_float(info.get("regularMarketPrice") or info.get("currentPrice")),
            "pe_ratio": _to_float(info.get("trailingPE") or info.get("forwardPE")),
            "pb_ratio": _to_float(info.get("priceToBook")),
            "roe": _to_float(info.get("returnOnEquity")),
            "roa": _to_float(info.get("returnOnAssets")),
            "debt_to_equity": _to_float(info.get("debtToEquity")),
            "current_ratio": _to_float(info.get("currentRatio")),
            "market_cap": _to_float(info.get("marketCap")),
            "dividend_yield": _to_float(info.get("dividendYield")),
            "sector": info.get("sector") or "Unknown",
            "industry": info.get("industry") or "Unknown",
            "profit_margin": _to_float(info.get("profitMargins")),
            "revenue_growth": _to_float(info.get("revenueGrowth")),
        }
        _FUND_CACHE[symbol] = (now, result)
        return dict(result)
    except Exception:
        if cached:
            return dict(cached[1])
        return {}


def enrich_symbols(symbols: list[str], workers: int = 12) -> None:
    """Fetch missing fundamentals for the given symbols in parallel."""
    _load_disk_cache()
    missing = [s for s in symbols if not get_cached_fundamentals(s).get("current_price")]
    if not missing:
        return
    with ThreadPoolExecutor(max_workers=workers) as pool:
        list(pool.map(get_fundamentals, missing))
    _save_disk_cache()


def schedule_universe_warm(symbols: list[str]) -> None:
    """Fill remaining NSE fundamentals in the background."""
    global _warming
    with _disk_lock:
        if _warming:
            return
        _warming = True

    def run():
        try:
            enrich_symbols(symbols, workers=6)
        finally:
            global _warming
            with _disk_lock:
                _warming = False

    threading.Thread(target=run, daemon=True, name="stock-warm").start()