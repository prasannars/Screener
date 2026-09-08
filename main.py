from fastapi import FastAPI, UploadFile, File, Form, HTTPException, BackgroundTasks, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
import os
import tempfile
import asyncio
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Optional
import yfinance as yf

# Import existing modules
import cas_import
import portfolio_analyzer
import mutual_funds

# Import stock modules
import stock_analyzer
import screener
import screener_engine
import backtester
from ai_recommender import generate_stock_insight, generate_mf_insight
from stock_metrics import get_fundamentals, get_cached_fundamentals, calculate_stock_score, enrich_symbols, schedule_universe_warm, _to_float
import nse_universe

app = FastAPI(title="PrasannaTrade Portfolio Analyzer API", version="5.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==========================================
# PORTFOLIO ANALYSIS ENDPOINTS
# ==========================================

@app.post("/api/analyze-cas")
async def analyze_cas_upload(
    file: UploadFile = File(...),
    password: str = Form(""),
    background_tasks: BackgroundTasks = None
):
    if not file.filename.endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files are allowed.")
    
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        tmp.write(await file.read())
        tmp_path = tmp.name

    try:
        if background_tasks:
            background_tasks.add_task(mutual_funds.schedule_warm, 160)
        catalog = mutual_funds.get_funds(refresh=False).get("rows", [])
        report = cas_import.analyze_cas(source=tmp_path, password=password, filename=file.filename, catalog=catalog)
        return {"success": True, "data": report}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to analyze CAS: {str(e)}")
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)

@app.post("/api/analyze-stocks")
async def analyze_stocks_upload(file: UploadFile = File(...)):
    if not file.filename.endswith(('.xlsx', '.xls', '.csv')):
        raise HTTPException(status_code=400, detail="Only Excel/CSV files are allowed.")
    try:
        file_content = await file.read()
        result = stock_analyzer.analyze_stock_portfolio(file_content, file.filename)
        if 'error' in result:
            raise HTTPException(status_code=400, detail=result['error'])
        return {"success": True, "data": result}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to analyze stocks: {str(e)}")

# ==========================================
# ALL STOCKS INDIA ENDPOINTS
# ==========================================

def _stock_row_from_listing(item: dict) -> dict:
    symbol = item["symbol"]
    cached = get_cached_fundamentals(symbol)
    roe = _to_float(cached.get("roe") if cached else None)
    if roe is not None and roe < 1:
        roe = round(roe * 100, 2)
    pe = _to_float(cached.get("pe_ratio") if cached else None)
    price = _to_float(cached.get("current_price") if cached else None)
    score_data = calculate_stock_score(cached) if cached else {}
    return {
        "symbol": symbol,
        "name": (cached.get("name") if cached else None) or item.get("name") or symbol,
        "current_price": price,
        "pe_ratio": round(pe, 2) if pe is not None else None,
        "pb_ratio": _to_float(cached.get("pb_ratio") if cached else None),
        "roe": roe,
        "debt_to_equity": _to_float(cached.get("debt_to_equity") if cached else None),
        "market_cap": _to_float(cached.get("market_cap") if cached else None),
        "sector": (cached.get("sector") if cached else None) or item.get("industry") or "Unknown",
        "industry": (cached.get("industry") if cached else None) or item.get("industry"),
        "dividend_yield": _to_float(cached.get("dividend_yield") if cached else None),
        "score": _to_float(score_data.get("score")),
        "grade": score_data.get("grade"),
        "reasons": (score_data.get("reasons") or [])[:3],
    }

def _listed_universe() -> list[dict]:
    listed = nse_universe.load_listed_equities()
    if listed:
        return listed
    return [{"symbol": s, "name": s, "industry": None, "series": "EQ"} for s in dict.fromkeys(screener.STOCK_UNIVERSE)]

@app.get("/api/stocks/all")
async def get_all_stocks(
    limit: int = Query(100, ge=1, le=200),
    offset: int = Query(0, ge=0),
    sector: Optional[str] = None,
    q: Optional[str] = None,
    sort_by: str = Query("name", pattern="^(score|pe|roe|market_cap|name|symbol|price|sector)$"),
    sort_dir: str = Query("asc", pattern="^(asc|desc)$"),
):
    try:
        universe = _listed_universe()
        if q:
            needle = q.strip().lower()
            universe = [item for item in universe if needle in item["symbol"].lower() or needle in (item.get("name") or "").lower()]

        stocks_data = [_stock_row_from_listing(item) for item in universe]
        sectors = sorted({row.get("sector") for row in stocks_data if row.get("sector") and row.get("sector") != "Unknown"})

        if sector:
            wanted = sector.lower()
            stocks_data = [row for row in stocks_data if (row.get("sector") or "").lower() == wanted]

        reverse = sort_dir == "desc"
        missing_low, missing_high = -10**18, 10**18

        def num_key(row, field, missing):
            value = _to_float(row.get(field))
            return missing if value is None else value

        if sort_by == "score":
            stocks_data.sort(key=lambda x: num_key(x, "score", missing_low), reverse=reverse)
        elif sort_by == "pe":
            stocks_data.sort(key=lambda x: num_key(x, "pe_ratio", missing_high), reverse=reverse)
        elif sort_by == "roe":
            stocks_data.sort(key=lambda x: num_key(x, "roe", missing_low), reverse=reverse)
        elif sort_by == "market_cap":
            stocks_data.sort(key=lambda x: num_key(x, "market_cap", missing_low), reverse=reverse)
        elif sort_by == "price":
            stocks_data.sort(key=lambda x: num_key(x, "current_price", missing_low), reverse=reverse)
        elif sort_by == "symbol":
            stocks_data.sort(key=lambda x: str(x.get("symbol") or "").lower(), reverse=reverse)
        elif sort_by == "sector":
            stocks_data.sort(key=lambda x: str(x.get("sector") or "").lower(), reverse=reverse)
        else:
            stocks_data.sort(key=lambda x: str(x.get("name") or x.get("symbol") or "").lower(), reverse=reverse)

        total = len(stocks_data)
        page_items = stocks_data[offset:offset + limit]
        enrich_symbols([row["symbol"] for row in page_items], workers=12)
        paginated = [_stock_row_from_listing(item) for item in [
            {"symbol": row["symbol"], "name": row.get("name"), "industry": row.get("industry") or row.get("sector")}
            for row in page_items
        ]]
        schedule_universe_warm([row["symbol"] for row in stocks_data])
        return {
            "success": True,
            "data": paginated,
            "sectors": sectors,
            "pagination": {"total": total, "limit": limit, "offset": offset, "has_more": offset + limit < total},
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch stocks: {str(e)}")

# ==========================================
# ALL MUTUAL FUNDS ENDPOINTS
# ==========================================

@app.get("/api/mutual-funds/all")
async def get_all_mutual_funds(
    limit: int = Query(100, ge=1, le=200),
    offset: int = Query(0, ge=0),
    category: Optional[str] = None,
    bucket: Optional[str] = None,
    plan: Optional[str] = None,
    q: Optional[str] = None,
    sort_by: str = Query("name", pattern="^(ai_score|ret_1y|ret_3y|nav|name|category)$"),
    sort_dir: str = Query("asc", pattern="^(asc|desc)$"),
):
    try:
        funds_data = mutual_funds.get_funds(refresh=False)
        rows = funds_data.get("rows", [])
        filtered = rows
        if q:
            needle = q.strip().lower()
            filtered = [r for r in filtered if needle in (r.get("name") or "").lower() or needle in (r.get("amc") or "").lower() or needle in (r.get("code") or "")]
        if category:
            filtered = [r for r in filtered if r.get('category', '').lower() == category.lower()]
        if bucket:
            filtered = [r for r in filtered if r.get('bucket', '').lower() == bucket.lower()]
        if plan:
            filtered = [r for r in filtered if r.get('plan', '').lower() == plan.lower()]
        
        reverse = sort_dir == "desc"
        def fund_num(row, field, missing):
            try:
                value = row.get(field)
                if value is None or value == "": return missing
                return float(value)
            except (TypeError, ValueError):
                return missing

        if sort_by == 'ai_score':
            filtered.sort(key=lambda x: fund_num(x, 'ai_score', -1), reverse=reverse)
        elif sort_by == 'ret_1y':
            filtered.sort(key=lambda x: fund_num(x, 'ret_1y', -999), reverse=reverse)
        elif sort_by == 'ret_3y':
            filtered.sort(key=lambda x: fund_num(x, 'ret_3y', -999), reverse=reverse)
        elif sort_by == 'nav':
            filtered.sort(key=lambda x: fund_num(x, 'nav', -1), reverse=reverse)
        elif sort_by == 'category':
            filtered.sort(key=lambda x: str(x.get('category') or x.get('bucket') or '').lower(), reverse=reverse)
        else:
            filtered.sort(key=lambda x: str(x.get('name') or '').lower(), reverse=reverse)
        
        total = len(filtered)
        paginated = filtered[offset:offset + limit]
        codes = [row.get("code") for row in paginated if row.get("code")]
        if codes:
            mutual_funds.get_returns(codes)
            mutual_funds.merge_cached_returns(paginated)
        
        return {
            "success": True,
            "data": paginated,
            "pagination": {"total": total, "limit": limit, "offset": offset, "has_more": offset + limit < total},
            "as_of": funds_data.get("as_of")
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch mutual funds: {str(e)}")

@app.get("/api/mutual-funds/categories")
async def get_mf_categories():
    try:
        funds_data = mutual_funds.get_funds(refresh=False)
        rows = funds_data.get("rows", [])
        categories = sorted(list(set(r.get('category', '') for r in rows if r.get('category'))))
        buckets = sorted(list(set(r.get('bucket', '') for r in rows if r.get('bucket'))))
        return {"success": True, "data": {"categories": categories, "buckets": buckets}}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch categories: {str(e)}")

# ==========================================
# RECOMMENDATIONS & AI ENDPOINTS
# ==========================================

@app.get("/api/recommendations/stocks")
def get_grouped_stocks():
    payload = screener_engine.get_pro_themed_stock_recommendations()
    meta = payload.pop("_meta", {}) if isinstance(payload, dict) else {}
    return {"success": True, "data": payload, **meta}

@app.get("/api/recommendations/mutual-funds")
def get_grouped_mfs():
    return {"success": True, "data": screener_engine.get_grouped_mf_recommendations()}

@app.get("/api/ai/stock-insight/{symbol}")
def get_ai_stock_insight(symbol: str):
    fund = get_fundamentals(symbol)
    if not fund:
        return {"success": False, "error": "Stock not found"}
    return {"success": True, "symbol": symbol, "insight": generate_stock_insight(symbol, fund)}

@app.get("/api/ai/mf-insight/{code}")
def get_ai_mf_insight(code: str):
    funds_data = mutual_funds.get_funds(refresh=False)
    fund = next((r for r in funds_data.get("rows", []) if r.get("code") == code), None)
    if not fund:
        return {"success": False, "error": "Fund not found"}
    insight = generate_mf_insight(fund.get("name"), fund.get("category"), fund.get("ret_1y", 0), fund.get("ret_3y", 0), fund.get("ai_score", 0.5))
    return {"success": True, "name": fund.get("name"), "insight": insight}

@app.get("/api/backtest")
def run_backtest(symbols: str = Query("RELIANCE,TCS,HDFCBANK"), strategy: str = "SMA_Crossover", years: int = 3):
    symbol_list = [s.strip().upper() for s in symbols.split(",") if s.strip()]
    return {"success": True, "data": backtester.backtest_strategy(symbol_list, strategy, years)}

# ==========================================
# LIVE MARKET ENDPOINTS
# ==========================================

def _last_price(symbol: str) -> tuple[str, Optional[float]]:
    try:
        info = yf.Ticker(f"{symbol}.NS").fast_info
        try:
            price = info["last_price"]
        except Exception:
            price = getattr(info, "last_price", None)
        if price is not None:
            return symbol, round(float(price), 2)
    except Exception:
        pass
    return symbol, None

def fetch_live_quotes(symbols: list[str]) -> dict:
    quotes = {}
    if not symbols: return quotes
    workers = min(16, len(symbols))
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = [pool.submit(_last_price, symbol) for symbol in symbols]
        for fut in as_completed(futures):
            symbol, price = fut.result()
            if price is not None:
                quotes[symbol] = price
    return quotes

@app.get("/api/live/quotes")
def get_live_quotes(symbols: str = Query("RELIANCE,TCS,HDFCBANK,INFY,ITC")):
    symbol_list = [s.strip().upper() for s in symbols.split(",") if s.strip()][:60]
    return {"success": True, "data": fetch_live_quotes(symbol_list)}

@app.get("/api/live/market")
def get_live_market(limit: int = Query(80, ge=1, le=200), offset: int = Query(0, ge=0), q: Optional[str] = None):
    universe = _listed_universe()
    if q:
        needle = q.strip().lower()
        universe = [item for item in universe if needle in item["symbol"].lower() or needle in (item.get("name") or "").lower()]
        universe.sort(key=lambda item: str(item.get("symbol") or ""))
    else:
        core_order = {symbol: idx for idx, symbol in enumerate(screener_engine.CORE_SYMBOLS)}
        core_rows = [item for item in universe if item.get("symbol") in core_order]
        rest = [item for item in universe if item.get("symbol") not in core_order]
        core_rows.sort(key=lambda item: core_order.get(item.get("symbol"), 999))
        rest.sort(key=lambda item: str(item.get("symbol") or ""))
        universe = core_rows + rest
    total = len(universe)
    page = universe[offset:offset + limit]
    rows = []
    for item in page:
        symbol = item["symbol"]
        cached = get_cached_fundamentals(symbol) or {}
        price = _to_float(cached.get("current_price"))
        rows.append({
            "symbol": symbol,
            "name": cached.get("name") or item.get("name") or symbol,
            "price": round(price, 2) if price is not None else None,
            "sector": cached.get("sector") or item.get("industry"),
        })
    return {
        "success": True,
        "data": rows,
        "pagination": {"total": total, "limit": limit, "offset": offset, "has_more": offset + limit < total},
    }

async def live_stock_data_generator(symbols: list[str]):
    while True:
        try:
            data = await asyncio.to_thread(fetch_live_quotes, symbols)
            yield f"data: {json.dumps(data)}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)})}\n\n"
        await asyncio.sleep(2)

@app.get("/api/live/stocks")
async def stream_live_stocks(symbols: str = Query("RELIANCE,TCS,HDFCBANK,INFY,ITC")):
    symbol_list = [s.strip().upper() for s in symbols.split(",") if s.strip()]
    return StreamingResponse(
        live_stock_data_generator(symbol_list),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive", "X-Accel-Buffering": "no"},
    )

@app.get("/api/health")
def health_check():
    return {"status": "ok", "message": "PrasannaTrade Analyzer v5.0 is running"}
# ==========================================
# STOCK DETAIL & COMPARISON ENDPOINTS
# ==========================================

@app.get("/api/stocks/{symbol}/details")
async def get_stock_details_enhanced(symbol: str):
    """Comprehensive stock details with peers"""
    try:
        fund = get_fundamentals(symbol)
        if not fund:
            raise HTTPException(status_code=404, detail="Stock not found")
        score_data = calculate_stock_score(fund)
        sector = fund.get('sector', '')
        universe = _listed_universe()
        peers = [_stock_row_from_listing(item) for item in universe if (item.get("industry") or "").lower() == (sector or "").lower() and item["symbol"] != symbol][:5]
        return {
            "success": True,
            "data": {
                "basic": {"symbol": symbol, "name": fund.get('name'), "sector": fund.get('sector'), "industry": fund.get('industry'), "current_price": fund.get('current_price'), "market_cap": fund.get('market_cap')},
                "fundamentals": {"pe_ratio": fund.get('pe_ratio'), "pb_ratio": fund.get('pb_ratio'), "roe": fund.get('roe'), "roce": fund.get('roce'), "debt_to_equity": fund.get('debt_to_equity'), "current_ratio": fund.get('current_ratio'), "profit_margin": fund.get('profit_margin'), "revenue_growth": fund.get('revenue_growth'), "dividend_yield": fund.get('dividend_yield')},
                "valuation": {"52w_high": fund.get('52w_high'), "52w_low": fund.get('52w_low'), "avg_volume": fund.get('avg_volume')},
                "score": {"fundamental_score": score_data.get('score'), "grade": score_data.get('grade'), "reasons": score_data.get('reasons', [])},
                "peers": peers,
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/mutual-funds/{code}/details")
async def get_mf_details_enhanced(code: str):
    """Comprehensive MF details with risk metrics"""
    try:
        funds_data = mutual_funds.get_funds(refresh=False)
        rows = funds_data.get("rows", [])
        fund = next((r for r in rows if r.get('code') == code), None)
        if not fund:
            raise HTTPException(status_code=404, detail="Fund not found")
        mutual_funds.get_returns([code])
        mutual_funds.merge_cached_returns([fund])
        return {
            "success": True,
            "data": {
                "basic": {"name": fund.get('name'), "amc": fund.get('amc'), "category": fund.get('category'), "bucket": fund.get('bucket'), "plan": fund.get('plan'), "option": fund.get('option'), "nav": fund.get('nav'), "nav_date": fund.get('nav_date')},
                "returns": {"ret_1m": fund.get('ret_1m'), "ret_3m": fund.get('ret_3m'), "ret_6m": fund.get('ret_6m'), "ret_1y": fund.get('ret_1y'), "ret_3y": fund.get('ret_3y'), "ret_5y": fund.get('ret_5y')},
                "risk_metrics": {"vol_1y": fund.get('vol_1y'), "max_dd_1y": fund.get('max_dd_1y'), "sharpe_1y": fund.get('sharpe_1y'), "beta": fund.get('beta'), "alpha": fund.get('alpha')},
                "ai_score": fund.get('ai_score'),
                "quality": fund.get('quality'),
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/mutual-funds/compare")
async def compare_mutual_funds(codes: list[str]):
    """Compare 2-4 mutual funds side by side"""
    try:
        if len(codes) < 2 or len(codes) > 4:
            raise HTTPException(status_code=400, detail="Compare 2-4 funds")
        funds_data = mutual_funds.get_funds(refresh=False)
        rows = funds_data.get("rows", [])
        comparison = []
        for code in codes:
            fund = next((r for r in rows if r.get('code') == code), None)
            if fund:
                mutual_funds.get_returns([code])
                mutual_funds.merge_cached_returns([fund])
                comparison.append({
                    "code": code, "name": fund.get('name'), "amc": fund.get('amc'),
                    "category": fund.get('category'), "nav": fund.get('nav'),
                    "ret_1y": fund.get('ret_1y'), "ret_3y": fund.get('ret_3y'), "ret_5y": fund.get('ret_5y'),
                    "vol_1y": fund.get('vol_1y'), "sharpe_1y": fund.get('sharpe_1y'),
                    "max_dd_1y": fund.get('max_dd_1y'), "ai_score": fund.get('ai_score'),
                })
        return {"success": True, "data": comparison}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
