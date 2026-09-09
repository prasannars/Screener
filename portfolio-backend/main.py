from fastapi import FastAPI, UploadFile, File, Form, HTTPException, BackgroundTasks, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
import os
import tempfile
import asyncio
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Optional, Dict
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
import portfolio_store

app = FastAPI(title="PrasannaTrade Portfolio Analyzer API", version="5.0.0")

# CORS middleware
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
    """Analyze mutual fund CAS PDF"""
    if not file.filename.endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files are allowed.")
    
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        tmp.write(await file.read())
        tmp_path = tmp.name

    try:
        if background_tasks:
            background_tasks.add_task(mutual_funds.schedule_warm, 160)
            
        catalog = mutual_funds.get_funds(refresh=False).get("rows", [])
        
        report = cas_import.analyze_cas(
            source=tmp_path, 
            password=password, 
            filename=file.filename,
            catalog=catalog
        )
        
        return {"success": True, "data": report}
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        message = str(e)
        if "password" in message.lower():
            raise HTTPException(status_code=400, detail=message)
        raise HTTPException(status_code=500, detail=f"Failed to analyze CAS: {message}")
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)

@app.post("/api/analyze-stocks")
async def analyze_stocks_upload(file: UploadFile = File(...), password: str = Form("")):
    """Analyze stock portfolio from Excel/CSV or equities in an NSDL/CDSL CAS PDF."""
    name = (file.filename or "").lower()
    if not name.endswith((".xlsx", ".xls", ".csv", ".pdf")):
        raise HTTPException(status_code=400, detail="Only Excel, CSV, or CAS PDF files are allowed.")

    try:
        file_content = await file.read()
        if name.endswith(".pdf"):
            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
                tmp.write(file_content)
                tmp_path = tmp.name
            try:
                cas_data = cas_import.parse_cas(tmp_path, password)
                holdings = cas_import.extract_cas_equities(cas_data)
                result = stock_analyzer.analyze_parsed_holdings(holdings)
            finally:
                if os.path.exists(tmp_path):
                    os.remove(tmp_path)
        else:
            result = stock_analyzer.analyze_stock_portfolio(file_content, file.filename, password=password)

        if "error" in result:
            raise HTTPException(status_code=400, detail=result["error"])

        return {"success": True, "data": result}

    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        message = str(e)
        if "password" in message.lower():
            raise HTTPException(status_code=400, detail=message)
        raise HTTPException(status_code=500, detail=f"Failed to analyze stocks: {message}")

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
    return [{"symbol": s, "name": s, "industry": None, "series": "EQ"} for s in dict.fromkeys(screener.SCREEN_UNIVERSE)]

@app.get("/api/stocks/all")
async def get_all_stocks(
    limit: int = Query(100, ge=1, le=200),
    offset: int = Query(0, ge=0),
    sector: Optional[str] = None,
    q: Optional[str] = None,
    sort_by: str = Query("name", pattern="^(score|pe|roe|market_cap|name|symbol|price|sector)$"),
    sort_dir: str = Query("asc", pattern="^(asc|desc)$"),
):
    """Paginated NSE listed stocks. Fundamentals overlay cached yfinance data when available."""
    try:
        universe = _listed_universe()
        if q:
            needle = q.strip().lower()
            universe = [
                item for item in universe
                if needle in item["symbol"].lower() or needle in (item.get("name") or "").lower()
            ]

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
            "pagination": {
                "total": total,
                "limit": limit,
                "offset": offset,
                "has_more": offset + limit < total,
            },
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch stocks: {str(e)}")

@app.get("/api/stocks/{symbol}")
async def get_stock_details(symbol: str):
    """Get detailed information for a specific stock"""
    try:
        fund = get_fundamentals(symbol)
        if not fund:
            raise HTTPException(status_code=404, detail="Stock not found")
        
        from stock_metrics import calculate_stock_score
        score_data = calculate_stock_score(fund)
        
        return {
            "success": True,
            "data": {
                **fund,
                'score': score_data.get('score'),
                'grade': score_data.get('grade'),
                'reasons': score_data.get('reasons')
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch stock: {str(e)}")

@app.get("/api/stocks/screen/recommended")
async def get_recommended_stocks(limit: int = Query(10, ge=1, le=50)):
    """Get top recommended stocks based on fundamental screening"""
    try:
        screened = screener.screen_stocks(limit=limit, min_score=60)
        return {"success": True, "data": screened}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to screen stocks: {str(e)}")

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
    """
    Get all Indian mutual funds from AMFI catalog.
    Returns paginated list with returns and AI scores.
    """
    try:
        funds_data = mutual_funds.get_funds(refresh=False)
        rows = funds_data.get("rows", [])
        
        # Apply filters
        filtered = rows
        if q:
            needle = q.strip().lower()
            filtered = [
                r for r in filtered
                if needle in (r.get("name") or "").lower()
                or needle in (r.get("amc") or "").lower()
                or needle in (r.get("code") or "")
            ]
        if category:
            filtered = [r for r in filtered if r.get('category', '').lower() == category.lower()]
        if bucket:
            filtered = [r for r in filtered if r.get('bucket', '').lower() == bucket.lower()]
        if plan:
            filtered = [r for r in filtered if r.get('plan', '').lower() == plan.lower()]
        
        # Sort
        reverse = sort_dir == "desc"

        def fund_num(row, field, missing):
            try:
                value = row.get(field)
                if value is None or value == "":
                    return missing
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
        
        # Paginate, then load 1Y/3Y for this page so the table is populated
        total = len(filtered)
        paginated = filtered[offset:offset + limit]
        codes = [row.get("code") for row in paginated if row.get("code")]
        if codes:
            mutual_funds.get_returns(codes)
            mutual_funds.merge_cached_returns(paginated)
        
        return {
            "success": True,
            "data": paginated,
            "pagination": {
                "total": total,
                "limit": limit,
                "offset": offset,
                "has_more": offset + limit < total
            },
            "as_of": funds_data.get("as_of")
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch mutual funds: {str(e)}")

@app.get("/api/mutual-funds/categories")
async def get_mf_categories():
    """Get all available mutual fund categories"""
    try:
        funds_data = mutual_funds.get_funds(refresh=False)
        rows = funds_data.get("rows", [])
        
        categories = sorted(list(set(r.get('category', '') for r in rows if r.get('category'))))
        buckets = sorted(list(set(r.get('bucket', '') for r in rows if r.get('bucket'))))
        
        return {
            "success": True,
            "data": {
                "categories": categories,
                "buckets": buckets
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch categories: {str(e)}")

@app.get("/api/mutual-funds/{code}")
async def get_mf_details(code: str):
    """Get detailed information for a specific mutual fund"""
    try:
        funds_data = mutual_funds.get_funds(refresh=False)
        rows = funds_data.get("rows", [])
        
        fund = next((r for r in rows if r.get('code') == code), None)
        if not fund:
            raise HTTPException(status_code=404, detail="Mutual fund not found")
        
        return {"success": True, "data": fund}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch fund: {str(e)}")

@app.get("/api/recommendations/stocks")
def get_grouped_stocks():
    return {"success": True, "data": screener_engine.get_grouped_stock_recommendations()}

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

def _last_price(symbol: str) -> tuple[str, Optional[float]]:
    """yfinance FastInfo.get('last_price') returns None; use keyed access instead."""
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
    if not symbols:
        return quotes
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
    symbol_list = [s.strip().upper() for s in symbols.split(",") if s.strip()][:40]
    return {"success": True, "data": fetch_live_quotes(symbol_list)}

@app.get("/api/live/market")
def get_live_market(
    limit: int = Query(80, ge=1, le=200),
    offset: int = Query(0, ge=0),
    q: Optional[str] = None,
):
    """Paginated NSE universe with cached last prices for the Live Market board."""
    universe = _listed_universe()
    if q:
        needle = q.strip().lower()
        universe = [
            item for item in universe
            if needle in item["symbol"].lower() or needle in (item.get("name") or "").lower()
        ]
    universe.sort(key=lambda item: str(item.get("symbol") or ""))
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
        "pagination": {
            "total": total,
            "limit": limit,
            "offset": offset,
            "has_more": offset + limit < total,
        },
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
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )

# ==========================================
# PORTFOLIO PERSISTENCE & RECOMMENDATIONS
# ==========================================

@app.post("/api/portfolio/save-stocks")
async def save_stock_portfolio(stocks: List[Dict]):
    """Save stock holdings to persistent storage."""
    try:
        count = portfolio_store.replace_stocks(stocks)
        return {"success": True, "message": f"Saved {count} stocks", "count": count}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/portfolio/save-mfs")
async def save_mf_portfolio(funds: List[Dict]):
    """Save mutual fund holdings to persistent storage."""
    try:
        count = portfolio_store.replace_mutual_funds(funds)
        return {"success": True, "message": f"Saved {count} mutual funds", "count": count}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/portfolio/stocks")
async def get_stored_stocks():
    """Retrieve all stored stocks."""
    try:
        stocks = portfolio_store.get_all_stocks()
        return {"success": True, "data": stocks, "count": len(stocks)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/portfolio/mfs")
async def get_stored_mfs():
    """Retrieve all stored mutual funds."""
    try:
        mfs = portfolio_store.get_all_mfs()
        return {"success": True, "data": mfs, "count": len(mfs)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/portfolio/snapshot")
async def get_portfolio_snapshot():
    """Saved holdings, last CAS/stock reports, and summary. Unchanged until the next upload."""
    try:
        return {"success": True, "data": portfolio_store.get_snapshot()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/portfolio/save-report")
async def save_portfolio_report(payload: Dict):
    """Store the last analysis JSON so the Portfolio tab can replay it."""
    try:
        kind = (payload.get("kind") or "").lower()
        report = payload.get("report")
        if kind not in ("mf", "stocks") or not isinstance(report, dict):
            raise HTTPException(status_code=400, detail="kind must be mf or stocks with a report object")
        prefix = "mf" if kind == "mf" else "stock"
        portfolio_store.set_meta(f"{prefix}_report", json.dumps(report))
        portfolio_store.set_meta(f"{prefix}_file", str(report.get("file") or ""))
        return {"success": True}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/portfolio/summary")
async def get_portfolio_summary():
    """Get portfolio summary statistics."""
    try:
        summary = portfolio_store.get_portfolio_summary()
        return {"success": True, "data": summary}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/portfolio/clear")
async def clear_portfolio_data():
    """Clear all portfolio data."""
    try:
        portfolio_store.clear_portfolio()
        return {"success": True, "message": "Portfolio cleared"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/portfolio/recommendations")
async def get_personalized_recommendations():
    """Generate personalized recommendations based on user's portfolio."""
    try:
        stocks = portfolio_store.get_all_stocks()
        mfs = portfolio_store.get_all_mfs()
        
        recommendations = {
            "stocks": analyze_stock_portfolio(stocks),
            "mutual_funds": analyze_mf_portfolio(mfs),
            "overall": analyze_overall_portfolio(stocks, mfs)
        }
        
        return {"success": True, "data": recommendations}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

def analyze_stock_portfolio(stocks: List[Dict]) -> Dict:
    """Analyze stock portfolio and generate recommendations."""
    if not stocks:
        return {"status": "empty", "recommendations": []}

    sector_allocation = {}
    total_value = 0
    for stock in stocks:
        sector = stock.get("sector") or "Unknown"
        value = stock.get("current_value", 0) or 0
        sector_allocation[sector] = sector_allocation.get(sector, 0) + value
        total_value += value
    for sector in sector_allocation:
        sector_allocation[sector] = round((sector_allocation[sector] / total_value * 100), 2) if total_value > 0 else 0

    recommendations = []
    for sector, pct in sector_allocation.items():
        if sector != "Unknown" and pct > 40:
            recommendations.append({
                "type": "warning",
                "category": "concentration",
                "title": f"{sector} is {pct:.0f}% of stocks",
                "message": "Trim the largest names in this sleeve and add a different sector so one cycle cannot sink the book.",
            })

    underperformers = [s for s in stocks if s.get("return_pct") is not None and s["return_pct"] < -10]
    for stock in underperformers[:2]:
        recommendations.append({
            "type": "review",
            "category": "performance",
            "title": f"{stock.get('symbol')} is down {stock['return_pct']:.1f}%",
            "message": "Re-read the thesis. Exit if the original reason to own it is gone; average down only if it is not.",
        })

    winners = [s for s in stocks if s.get("return_pct") is not None and s["return_pct"] > 50]
    for stock in winners[:2]:
        value_pct = (stock.get("current_value", 0) / total_value * 100) if total_value > 0 else 0
        if value_pct > 20:
            recommendations.append({
                "type": "opportunity",
                "category": "rebalancing",
                "title": f"Book some profit in {stock.get('symbol')}",
                "message": f"Up {stock['return_pct']:.0f}% and {value_pct:.0f}% of the stock book. Trim toward your original weight.",
            })

    return {
        "status": "analyzed",
        "count": len(stocks),
        "total_value": total_value,
        "sector_allocation": sector_allocation,
        "recommendations": recommendations[:4],
    }


def analyze_mf_portfolio(mfs: List[Dict]) -> Dict:
    """Analyze mutual fund portfolio and generate recommendations."""
    if not mfs:
        return {"status": "empty", "recommendations": []}

    category_counts = {}
    category_value = {}
    total_value = 0
    for mf in mfs:
        category = mf.get("category") or mf.get("bucket") or "Unknown"
        value = mf.get("current_value", 0) or mf.get("value", 0) or 0
        category_counts[category] = category_counts.get(category, 0) + 1
        category_value[category] = category_value.get(category, 0) + value
        total_value += value

    category_allocation = {
        cat: round((val / total_value * 100), 2) if total_value > 0 else 0
        for cat, val in category_value.items()
    }

    recommendations = []
    overlap = [cat for cat, n in category_counts.items() if cat != "Unknown" and n >= 3]
    if overlap:
        recommendations.append({
            "type": "warning",
            "category": "overlap",
            "title": f"{len(overlap)} categor{'y has' if len(overlap)==1 else 'ies have'} 3+ funds",
            "message": f"Too many schemes in {', '.join(overlap[:3])}. Keep the best Direct Growth fund and exit the rest.",
        })

    buckets = {(mf.get("bucket") or mf.get("category") or "").lower() for mf in mfs}
    blob = " ".join(buckets)
    if not any(x in blob for x in ("debt", "liquid", "overnight", "gilt")):
        recommendations.append({
            "type": "opportunity",
            "category": "diversification",
            "title": "No debt or liquid sleeve",
            "message": "Add a short-duration or liquid fund as 6–12 months of expenses so you are not forced to sell equity.",
        })

    losers = []
    for mf in mfs:
        ret = mf.get("return_pct") if mf.get("return_pct") is not None else mf.get("ret_pct")
        if ret is not None and ret < 0:
            losers.append((mf, ret))
    losers.sort(key=lambda x: x[1])
    for mf, ret in losers[:2]:
        name = mf.get("scheme_name") or mf.get("name") or "A fund"
        recommendations.append({
            "type": "review",
            "category": "performance",
            "title": f"{name[:48]} is {ret:.1f}%",
            "message": "Compare 3Y and 5Y vs its category. Switch to a stronger Direct Growth peer if the lag is structural.",
        })

    return {
        "status": "analyzed",
        "count": len(mfs),
        "total_value": total_value,
        "category_allocation": category_allocation,
        "recommendations": recommendations[:4],
    }


def analyze_overall_portfolio(stocks: List[Dict], mfs: List[Dict]) -> Dict:
    """Analyze overall portfolio (stocks + MFs)."""
    stock_value = sum(s.get("current_value", 0) or 0 for s in stocks)
    mf_value = sum(m.get("current_value", 0) or m.get("value", 0) or 0 for m in mfs)
    total_value = stock_value + mf_value

    if total_value == 0:
        return {"status": "empty", "recommendations": []}

    stock_pct = round((stock_value / total_value * 100), 2)
    mf_pct = round((mf_value / total_value * 100), 2)
    recommendations = []

    if stocks and mfs:
        recommendations.append({
            "type": "opportunity",
            "category": "allocation",
            "title": f"{stock_pct:.0f}% stocks · {mf_pct:.0f}% funds",
            "message": "Direct equity is for high conviction. Let funds cover the rest of the market so you are not over-trading.",
        })
    elif stock_pct > 80:
        recommendations.append({
            "type": "warning",
            "category": "risk",
            "title": f"{stock_pct:.0f}% is direct stocks",
            "message": "Add a debt or hybrid fund so a market drawdown does not force you to sell shares for cash.",
        })
    elif mf_pct > 90:
        recommendations.append({
            "type": "opportunity",
            "category": "growth",
            "title": "Almost no direct stocks",
            "message": "A small satellite of 4–8 quality names can sit beside your funds if you want extra equity tilt.",
        })

    return {
        "status": "analyzed",
        "stock_allocation": stock_pct,
        "mf_allocation": mf_pct,
        "total_value": total_value,
        "recommendations": recommendations,
    }

@app.get("/api/health")
def health_check():
    return {"status": "ok", "message": "PrasannaTrade Analyzer v5.0 is running"}