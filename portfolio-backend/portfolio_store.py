"""
Portfolio persistence using SQLite.
Stores uploaded stocks and mutual funds for personalized recommendations.
"""
import sqlite3
import json
import os
from datetime import datetime
from typing import List, Dict, Optional

DB_PATH = "data/portfolio.db"

def init_db():
    """Initialize the database with required tables."""
    os.makedirs("data", exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS stock_portfolio (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol TEXT UNIQUE NOT NULL,
            name TEXT,
            quantity REAL,
            buy_price REAL,
            buy_date TEXT,
            current_price REAL,
            current_value REAL,
            invested_value REAL,
            gain_loss REAL,
            return_pct REAL,
            sector TEXT,
            industry TEXT,
            added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS mf_portfolio (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            scheme_code TEXT UNIQUE,
            scheme_name TEXT NOT NULL,
            amc TEXT,
            category TEXT,
            bucket TEXT,
            units REAL,
            invested_value REAL,
            current_value REAL,
            current_nav REAL,
            gain_loss REAL,
            return_pct REAL,
            added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS portfolio_meta (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    """)
    
    conn.commit()
    conn.close()

def save_stocks(stocks: List[Dict]) -> int:
    """Save or update stock holdings."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    count = 0
    for stock in stocks:
        if not stock.get('symbol'):
            continue
        cursor.execute("""
            INSERT INTO stock_portfolio (symbol, name, quantity, buy_price, buy_date, 
                                        current_price, current_value, invested_value, 
                                        gain_loss, return_pct, sector, industry)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(symbol) DO UPDATE SET
                name = excluded.name,
                quantity = excluded.quantity,
                buy_price = excluded.buy_price,
                buy_date = excluded.buy_date,
                current_price = excluded.current_price,
                current_value = excluded.current_value,
                invested_value = excluded.invested_value,
                gain_loss = excluded.gain_loss,
                return_pct = excluded.return_pct,
                sector = excluded.sector,
                industry = excluded.industry,
                updated_at = CURRENT_TIMESTAMP
        """, (
            stock.get('symbol'),
            stock.get('name'),
            stock.get('quantity'),
            stock.get('buy_price'),
            stock.get('buy_date'),
            stock.get('current_price'),
            stock.get('current_value'),
            stock.get('invested'),
            stock.get('gain'),
            stock.get('return_pct'),
            stock.get('sector'),
            stock.get('industry')
        ))
        count += 1
    
    conn.commit()
    conn.close()
    return count

def save_mutual_funds(funds: List[Dict]) -> int:
    """Save or update mutual fund holdings."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    count = 0
    for fund in funds:
        name = fund.get('name')
        if not name:
            continue
        cursor.execute("""
            INSERT INTO mf_portfolio (scheme_code, scheme_name, amc, category, bucket,
                                     units, invested_value, current_value, current_nav,
                                     gain_loss, return_pct)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(scheme_code) DO UPDATE SET
                scheme_name = excluded.scheme_name,
                amc = excluded.amc,
                category = excluded.category,
                bucket = excluded.bucket,
                units = excluded.units,
                invested_value = excluded.invested_value,
                current_value = excluded.current_value,
                current_nav = excluded.current_nav,
                gain_loss = excluded.gain_loss,
                return_pct = excluded.return_pct,
                updated_at = CURRENT_TIMESTAMP
        """, (
            fund.get('code') or fund.get('amfi_code') or fund.get('isin') or fund.get('name'),
            fund.get('name'),
            fund.get('amc'),
            fund.get('category'),
            fund.get('bucket'),
            fund.get('units'),
            fund.get('invested'),
            fund.get('value'),
            fund.get('current_nav'),
            fund.get('gain'),
            fund.get('ret_pct')
        ))
        count += 1
    
    conn.commit()
    conn.close()
    return count

def replace_stocks(stocks: List[Dict]) -> int:
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM stock_portfolio")
    conn.commit()
    conn.close()
    count = save_stocks(stocks)
    set_meta("stock_updated_at", datetime.utcnow().isoformat() + "Z")
    return count


def replace_mutual_funds(funds: List[Dict]) -> int:
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM mf_portfolio")
    conn.commit()
    conn.close()
    count = save_mutual_funds(funds)
    set_meta("mf_updated_at", datetime.utcnow().isoformat() + "Z")
    return count


def set_meta(key: str, value: Optional[str]) -> None:
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    if value is None:
        cursor.execute("DELETE FROM portfolio_meta WHERE key = ?", (key,))
    else:
        cursor.execute(
            "INSERT INTO portfolio_meta (key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value = excluded.value",
            (key, value),
        )
    conn.commit()
    conn.close()


def get_meta(key: str) -> Optional[str]:
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT value FROM portfolio_meta WHERE key = ?", (key,))
    row = cursor.fetchone()
    conn.close()
    return row[0] if row else None


def get_snapshot() -> Dict:
    def _json_meta(key: str):
        raw = get_meta(key)
        if not raw:
            return None
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return None

    stocks = get_all_stocks()
    mfs = get_all_mfs()
    summary = get_portfolio_summary()
    return {
        "stocks": stocks,
        "mutual_funds": mfs,
        "summary": summary,
        "mf_report": _json_meta("mf_report"),
        "stock_report": _json_meta("stock_report"),
        "mf_updated_at": get_meta("mf_updated_at"),
        "stock_updated_at": get_meta("stock_updated_at"),
        "mf_file": get_meta("mf_file"),
        "stock_file": get_meta("stock_file"),
    }


def get_all_stocks() -> List[Dict]:
    """Retrieve all stored stocks."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM stock_portfolio ORDER BY updated_at DESC")
    rows = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return rows

def get_all_mfs() -> List[Dict]:
    """Retrieve all stored mutual funds."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM mf_portfolio ORDER BY updated_at DESC")
    rows = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return rows

def get_portfolio_summary() -> Dict:
    """Get portfolio summary statistics."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("SELECT COUNT(*), SUM(invested_value), SUM(current_value) FROM stock_portfolio")
    stock_stats = cursor.fetchone()
    
    cursor.execute("SELECT COUNT(*), SUM(invested_value), SUM(current_value) FROM mf_portfolio")
    mf_stats = cursor.fetchone()
    
    conn.close()
    
    return {
        "stocks": {
            "count": stock_stats[0] or 0,
            "invested": stock_stats[1] or 0,
            "current": stock_stats[2] or 0,
            "gain_loss": (stock_stats[2] or 0) - (stock_stats[1] or 0)
        },
        "mutual_funds": {
            "count": mf_stats[0] or 0,
            "invested": mf_stats[1] or 0,
            "current": mf_stats[2] or 0,
            "gain_loss": (mf_stats[2] or 0) - (mf_stats[1] or 0)
        }
    }

def clear_portfolio():
    """Clear all portfolio data."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM stock_portfolio")
    cursor.execute("DELETE FROM mf_portfolio")
    conn.commit()
    conn.close()

# Initialize DB on import
init_db()