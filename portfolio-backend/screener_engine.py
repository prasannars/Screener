"""
Grouped screener: theme-based stock picks across the NSE list, plus
Direct Growth mutual funds by SEBI category.
"""
from __future__ import annotations

from typing import Dict, List

import mutual_funds
import nse_universe
from stock_metrics import _to_float, calculate_stock_score, get_cached_fundamentals

# Always include these even if cache is still warming.
CORE_SYMBOLS = [
    "RELIANCE", "TCS", "HDFCBANK", "INFY", "ICICIBANK", "HINDUNILVR", "ITC",
    "SBIN", "BHARTIARTL", "KOTAKBANK", "LT", "AXISBANK", "ASIANPAINT", "MARUTI",
    "SUNPHARMA", "TITAN", "BAJFINANCE", "WIPRO", "ULTRACEMCO", "NESTLEIND",
    "HCLTECH", "POWERGRID", "NTPC", "ONGC", "TATAMOTORS", "M&M", "JSWSTEEL",
    "TATASTEEL", "COALINDIA", "DRREDDY", "CIPLA", "GRASIM", "TECHM", "DIVISLAB",
    "PIDILITIND", "ABB", "SIEMENS", "HAVELLS", "DABUR", "GODREJCP",
]


def _pct(value) -> float:
    n = _to_float(value)
    if n is None:
        return 0.0
    return n * 100 if n < 1 else n


def _listed_items() -> list[dict]:
    listed = nse_universe.load_listed_equities()
    if listed:
        return listed
    return [{"symbol": s, "name": s, "industry": None} for s in CORE_SYMBOLS]


def get_pro_themed_stock_recommendations() -> Dict[str, List[Dict]]:
    """Screen every NSE listed stock that has cached fundamentals."""
    themes = {
        "Magic Formula (High ROE + Low PE)": [],
        "Quarterly Momentum (Turnaround/Growth)": [],
        "Piotroski Style (Strong Financials)": [],
        "Dividend Aristocrats": [],
        "Red Flags (Avoid)": [],
    }

    items = _listed_items()
    seen = set()
    scored = 0

    for item in items:
        symbol = (item.get("symbol") or "").upper()
        if not symbol or symbol in seen:
            continue
        seen.add(symbol)
        fund = get_cached_fundamentals(symbol)
        if not fund or not _to_float(fund.get("current_price")):
            continue
        scored += 1

        score_data = calculate_stock_score(fund)
        pe = _to_float(fund.get("pe_ratio"))
        if pe is None:
            pe = 999
        roe = _pct(fund.get("roe"))
        debt = _to_float(fund.get("debt_to_equity"))
        if debt is None:
            debt = 999
        div_yield = _pct(fund.get("dividend_yield"))
        profit_margin = _pct(fund.get("profit_margin"))
        revenue_growth = _pct(fund.get("revenue_growth"))

        stock_data = {
            "symbol": symbol,
            "price": _to_float(fund.get("current_price")),
            "pe": round(pe, 1) if pe < 900 else None,
            "roe": round(roe, 1) if roe else None,
            "score": score_data.get("score"),
            "sector": fund.get("sector") or item.get("industry"),
            "theme_reason": "",
        }

        if roe > 15 and pe < 25 and profit_margin > 10:
            row = dict(stock_data)
            row["theme_reason"] = f"ROE {roe:.1f}%, P/E {pe:.1f}, Margin {profit_margin:.1f}%"
            themes["Magic Formula (High ROE + Low PE)"].append(row)

        if revenue_growth > 15 and roe > 12:
            row = dict(stock_data)
            row["theme_reason"] = f"Rev Growth {revenue_growth:.1f}%, ROE {roe:.1f}%"
            themes["Quarterly Momentum (Turnaround/Growth)"].append(row)

        if roe > 0 and debt < 50 and profit_margin > 5:
            row = dict(stock_data)
            row["theme_reason"] = f"Low Debt ({debt:.1f}%), Positive Margin"
            themes["Piotroski Style (Strong Financials)"].append(row)

        if div_yield > 3.5 and debt < 100:
            row = dict(stock_data)
            row["theme_reason"] = f"Yield {div_yield:.2f}%"
            themes["Dividend Aristocrats"].append(row)

        if debt > 100 or roe < 0 or profit_margin < 0:
            reasons = []
            if debt > 100:
                reasons.append(f"High Debt ({debt:.1f}%)")
            if roe < 0:
                reasons.append("Negative ROE")
            if profit_margin < 0:
                reasons.append("Negative Margin")
            row = dict(stock_data)
            row["theme_reason"] = ", ".join(reasons)
            themes["Red Flags (Avoid)"].append(row)

    for name, group in themes.items():
        group.sort(key=lambda x: x.get("score") or 0, reverse=True)
        themes[name] = group[:12]

    themes["_meta"] = {
        "universe": len(seen),
        "with_fundamentals": scored,
    }
    return themes


def _mf_target(fund: dict) -> str | None:
    cat = f"{fund.get('category') or ''} {fund.get('bucket') or ''} {fund.get('cap') or ''}".lower()
    name = (fund.get("name") or "").lower()
    text = f"{cat} {name}"
    mapping = (
        ("large cap", "Large Cap"),
        ("mid cap", "Mid Cap"),
        ("small cap", "Small Cap"),
        ("flexi", "Flexi Cap"),
        ("multi cap", "Flexi Cap"),
        ("multicap", "Flexi Cap"),
        ("liquid", "Debt"),
        ("short duration", "Debt"),
        ("debt", "Debt"),
        ("gilt", "Debt"),
        ("overnight", "Debt"),
    )
    for needle, group in mapping:
        if needle in text:
            return group
    return None


def get_grouped_mf_recommendations() -> Dict[str, List[Dict]]:
    """Group Direct Growth schemes by SEBI-style category."""
    funds_data = mutual_funds.get_funds(refresh=False)
    rows = funds_data.get("rows", []) or []
    mutual_funds.merge_cached_returns(rows)
    direct_growth = [r for r in rows if r.get("plan") == "Direct" and r.get("option") == "Growth"]

    grouped = {"Large Cap": [], "Mid Cap": [], "Small Cap": [], "Flexi Cap": [], "Debt": []}
    pending_codes = []
    for fund in direct_growth:
        if _mf_target(fund) and fund.get("ret_1y") is None:
            code = fund.get("code")
            if code:
                pending_codes.append(code)

    if pending_codes:
        mutual_funds.get_returns(pending_codes[:120])
        mutual_funds.merge_cached_returns(direct_growth)

    for fund in direct_growth:
        target = _mf_target(fund)
        if not target:
            continue
        ret_1y = fund.get("ret_1y")
        if ret_1y is None:
            continue
        grouped[target].append({
            "name": fund.get("name"),
            "amc": fund.get("amc"),
            "ret_1y": round(float(ret_1y), 2),
            "ret_3y": round(float(fund["ret_3y"]), 2) if fund.get("ret_3y") is not None else None,
            "ret_5y": round(float(fund["ret_5y"]), 2) if fund.get("ret_5y") is not None else None,
            "ai_score": round(float(fund.get("ai_score") or 0.5), 2),
            "code": fund.get("code"),
        })

    for name, group in grouped.items():
        group.sort(key=lambda x: (x.get("ai_score") or 0, x.get("ret_3y") or -999, x.get("ret_1y") or -999), reverse=True)
        grouped[name] = group[:4]

    return grouped
