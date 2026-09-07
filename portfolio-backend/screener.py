"""
Stock screener module.
Screens NSE stocks based on fundamental criteria.
"""
from __future__ import annotations

from typing import List, Dict
import yfinance as yf

# Popular NSE stocks to screen (you can expand this list)
SCREEN_UNIVERSE = [
    'RELIANCE', 'TCS', 'HDFCBANK', 'INFY', 'ICICIBANK', 'HINDUNILVR',
    'ITC', 'SBIN', 'BHARTIARTL', 'KOTAKBANK', 'LT', 'AXISBANK',
    'ASIANPAINT', 'MARUTI', 'SUNPHARMA', 'TITAN', 'BAJFINANCE',
    'WIPRO', 'ULTRACEMCO', 'NESTLEIND', 'HCLTECH', 'POWERGRID',
    'NTPC', 'ONGC', 'TATAMOTORS', 'M&M', 'JSWSTEEL', 'TATASTEEL',
    'ADANIENT', 'ADANIPORTS', 'COALINDIA', 'BPCL', 'DRREDDY',
    'CIPLA', 'GRASIM', 'TECHM', 'DIVISLAB', 'HEROMOTOCO',
    'EICHERMOT', 'BAJAJFINSV', 'BAJAJ-AUTO', 'BRITANNIA', 'APOLLOHOSP',
    'TATACONSUM', 'HINDALCO', 'WIPRO', 'SBILIFE', 'INDUSINDBK'
]

def screen_stocks(limit: int = 10, min_score: int = 60) -> List[Dict]:
    """
    Screen stocks based on fundamental criteria:
    - P/E < 30
    - ROE > 15%
    - Debt-to-Equity < 100%
    - Market Cap > 1000 Cr
    
    Returns top stocks sorted by fundamental score.
    """
    from stock_metrics import calculate_stock_score, get_fundamentals
    
    screened = []
    
    for symbol in SCREEN_UNIVERSE:
        try:
            fundamentals = get_fundamentals(symbol)
            if not fundamentals:
                continue
            
            # Apply screening criteria
            pe = fundamentals.get('pe_ratio')
            roe = fundamentals.get('roe')
            debt_to_equity = fundamentals.get('debt_to_equity')
            market_cap = fundamentals.get('market_cap')
            
            # Convert ROE to percentage if needed
            roe_pct = roe * 100 if roe and roe < 1 else roe
            
            # Screening filters
            if pe and pe > 0 and pe < 30:
                if roe_pct and roe_pct > 15:
                    if debt_to_equity is None or debt_to_equity < 100:
                        if market_cap is None or market_cap > 100000000000:  # 1000 Cr
                            # Calculate score
                            score_data = calculate_stock_score(fundamentals)
                            
                            if score_data['score'] >= min_score:
                                screened.append({
                                    'symbol': symbol,
                                    'name': symbol,
                                    'score': score_data['score'],
                                    'grade': score_data['grade'],
                                    'reason': '; '.join(score_data['reasons'][:3]),
                                    'pe_ratio': pe,
                                    'roe': roe_pct,
                                    'debt_to_equity': debt_to_equity,
                                    'market_cap': market_cap,
                                    'sector': fundamentals.get('sector'),
                                    'current_price': fundamentals.get('current_price')
                                })
        except Exception as e:
            continue
    
    # Sort by score descending
    screened.sort(key=lambda x: x['score'], reverse=True)
    
    return screened[:limit]

def screen_by_sector(sector: str, limit: int = 5) -> List[Dict]:
    """
    Screen stocks by sector.
    """
    from stock_metrics import calculate_stock_score, get_fundamentals
    
    screened = []
    
    for symbol in SCREEN_UNIVERSE:
        try:
            fundamentals = get_fundamentals(symbol)
            if not fundamentals:
                continue
            
            if fundamentals.get('sector', '').lower() == sector.lower():
                score_data = calculate_stock_score(fundamentals)
                screened.append({
                    'symbol': symbol,
                    'name': symbol,
                    'score': score_data['score'],
                    'grade': score_data['grade'],
                    'reason': '; '.join(score_data['reasons'][:3]),
                    'sector': fundamentals.get('sector'),
                    'current_price': fundamentals.get('current_price')
                })
        except Exception as e:
            continue
    
    screened.sort(key=lambda x: x['score'], reverse=True)
    return screened[:limit]