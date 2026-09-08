"""
SMA crossover backtest using pandas (no vectorbt at import time).
"""
from __future__ import annotations

from datetime import datetime, timedelta

import pandas as pd
import yfinance as yf


def backtest_strategy(symbols: list[str], strategy: str = "SMA_Crossover", years: int = 3) -> dict:
    results = []
    end_date = datetime.now()
    start_date = end_date - timedelta(days=years * 365)
    yf_symbols = [f"{s}.NS" if not s.endswith((".NS", ".BO")) else s for s in symbols]

    data = yf.download(yf_symbols, start=start_date, end=end_date, progress=False, auto_adjust=True)
    if data is None or data.empty:
        return {"strategy": strategy, "period_years": years, "results": []}

    if isinstance(data.columns, pd.MultiIndex):
        close_prices = data["Close"]
    else:
        close_prices = data["Close"] if "Close" in data.columns else data

    for i, symbol in enumerate(symbols):
        try:
            col = yf_symbols[i]
            series = close_prices[col] if isinstance(close_prices, pd.DataFrame) else close_prices
            prices = series.dropna()
            if len(prices) < 200:
                continue

            fast = prices.rolling(50).mean()
            slow = prices.rolling(200).mean()
            pos = (fast > slow).astype(int)
            rets = prices.pct_change().fillna(0)
            strat = pos.shift(1).fillna(0) * rets
            equity = (1 + strat).cumprod()
            peak = equity.cummax()
            drawdown = (equity / peak - 1).min()
            trades = int((pos.diff().abs() == 1).sum())
            wins = int(((pos.shift(1).fillna(0) == 1) & (rets > 0)).sum())
            active_days = int((pos.shift(1).fillna(0) == 1).sum())
            mean = strat.mean()
            std = strat.std()
            sharpe = (mean / std * (252 ** 0.5)) if std and std > 0 else 0

            results.append({
                "symbol": symbol,
                "total_return_pct": round(float((equity.iloc[-1] - 1) * 100), 2),
                "sharpe_ratio": round(float(sharpe), 2),
                "max_drawdown_pct": round(float(drawdown * 100), 2),
                "total_trades": trades,
                "win_rate_pct": round((wins / active_days * 100), 2) if active_days else 0,
            })
        except Exception:
            continue

    results.sort(key=lambda x: x["total_return_pct"], reverse=True)
    return {"strategy": strategy, "period_years": years, "results": results}
