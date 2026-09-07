"""
Stock portfolio analysis module.
Parses stock holdings, fetches fundamentals via yfinance,
calculates returns, and generates recommendations.
"""
from __future__ import annotations

import re
from datetime import date, datetime
from typing import List, Dict, Optional
import pandas as pd
import yfinance as yf

from stock_metrics import calculate_stock_score, get_fundamentals
from screener import screen_stocks

def parse_stock_holdings_from_excel(raw: bytes, filename: str) -> List[Dict]:
    """
    Parse stock holdings from Excel/CSV.
    Expected columns: Symbol/Stock, Quantity, Buy Price, Buy Date, Current Price (optional)
    """
    try:
        if filename.lower().endswith('.csv'):
            df = pd.read_csv(pd.io.common.BytesIO(raw))
        else:
            df = pd.read_excel(pd.io.common.BytesIO(raw))
        
        holdings = []
        
        # Normalize column names
        col_map = {}
        for col in df.columns:
            col_lower = str(col).lower().strip()
            if any(x in col_lower for x in ['symbol', 'stock', 'ticker', 'name']):
                col_map['symbol'] = col
            elif any(x in col_lower for x in ['quantity', 'qty', 'shares', 'units']):
                col_map['quantity'] = col
            elif any(x in col_lower for x in ['buy price', 'purchase price', 'avg price', 'cost']):
                col_map['buy_price'] = col
            elif any(x in col_lower for x in ['buy date', 'purchase date', 'date']):
                col_map['buy_date'] = col
            elif any(x in col_lower for x in ['current price', 'ltp', 'cmp', 'market price']):
                col_map['current_price'] = col
        
        if 'symbol' not in col_map or 'quantity' not in col_map:
            return []
        
        for _, row in df.iterrows():
            try:
                symbol = str(row.get(col_map['symbol'], '')).strip().upper()
                if not symbol or symbol.lower() in ['nan', 'total']:
                    continue
                
                # Clean symbol (remove .NS, .BO suffixes if present)
                symbol = re.sub(r'\.(NS|BO|NSE|BSE)$', '', symbol)
                
                quantity = float(row.get(col_map['quantity'], 0))
                if quantity <= 0:
                    continue
                
                buy_price = float(row.get(col_map.get('buy_price', ''), 0))
                current_price = float(row.get(col_map.get('current_price', ''), 0))
                
                buy_date = None
                if 'buy_date' in col_map:
                    date_val = row.get(col_map['buy_date'])
                    if pd.notna(date_val):
                        if isinstance(date_val, datetime):
                            buy_date = date_val.date()
                        elif isinstance(date_val, date):
                            buy_date = date_val
                        else:
                            try:
                                buy_date = pd.to_datetime(str(date_val)).date()
                            except:
                                pass
                
                holdings.append({
                    'symbol': symbol,
                    'quantity': quantity,
                    'buy_price': buy_price,
                    'current_price': current_price,
                    'buy_date': buy_date,
                    'invested': buy_price * quantity if buy_price > 0 else 0,
                    'current_value': current_price * quantity if current_price > 0 else 0
                })
            except Exception as e:
                continue
        
        return holdings
    except Exception as e:
        return []

def fetch_stock_fundamentals(symbols: List[str]) -> Dict[str, Dict]:
    """
    Fetch fundamentals for a list of stock symbols using yfinance.
    Returns dict: symbol -> {pe, pb, roe, roa, debt_to_equity, market_cap, sector, industry, ...}
    """
    fundamentals = {}
    
    for symbol in symbols:
        try:
            # Append .NS for NSE stocks
            yf_symbol = f"{symbol}.NS"
            ticker = yf.Ticker(yf_symbol)
            
            info = ticker.info
            if not info or info.get('regularMarketPrice') is None:
                # Try BSE
                yf_symbol = f"{symbol}.BO"
                ticker = yf.Ticker(yf_symbol)
                info = ticker.info
            
            if not info:
                continue
            
            current_price = info.get('regularMarketPrice') or info.get('currentPrice') or 0
            
            fundamentals[symbol] = {
                'current_price': current_price,
                'pe_ratio': info.get('trailingPE') or info.get('forwardPE'),
                'pb_ratio': info.get('priceToBook'),
                'peg_ratio': info.get('pegRatio'),
                'roe': info.get('returnOnEquity'),
                'roa': info.get('returnOnAssets'),
                'debt_to_equity': info.get('debtToEquity'),
                'current_ratio': info.get('currentRatio'),
                'market_cap': info.get('marketCap'),
                'dividend_yield': info.get('dividendYield'),
                'sector': info.get('sector', 'Unknown'),
                'industry': info.get('industry', 'Unknown'),
                'beta': info.get('beta'),
                '52w_high': info.get('fiftyTwoWeekHigh'),
                '52w_low': info.get('fiftyTwoWeekLow'),
                'avg_volume': info.get('averageVolume'),
                'eps': info.get('trailingEps'),
                'book_value': info.get('bookValue'),
                'profit_margin': info.get('profitMargins'),
                'operating_margin': info.get('operatingMargins'),
                'revenue_growth': info.get('revenueGrowth'),
                'earnings_growth': info.get('earningsGrowth')
            }
        except Exception as e:
            continue
    
    return fundamentals

def calculate_stock_returns(holdings: List[Dict], fundamentals: Dict[str, Dict]) -> List[Dict]:
    """
    Update holdings with current prices, returns, and holding period.
    """
    today = date.today()
    
    for h in holdings:
        symbol = h['symbol']
        
        # Update current price from fundamentals
        if symbol in fundamentals and fundamentals[symbol].get('current_price'):
            h['current_price'] = fundamentals[symbol]['current_price']
        
        # Calculate values
        if h['buy_price'] > 0 and h['quantity'] > 0:
            h['invested'] = h['buy_price'] * h['quantity']
        
        if h['current_price'] > 0 and h['quantity'] > 0:
            h['current_value'] = h['current_price'] * h['quantity']
        
        if h['invested'] > 0 and h['current_value'] > 0:
            h['gain'] = h['current_value'] - h['invested']
            h['return_pct'] = round((h['gain'] / h['invested']) * 100, 2)
        else:
            h['gain'] = 0
            h['return_pct'] = 0
        
        # Calculate holding period
        if h.get('buy_date'):
            days_held = (today - h['buy_date']).days
            h['holding_years'] = round(days_held / 365.25, 2)
            
            # Determine if LTCG or STCG
            if days_held > 365:
                h['tax_type'] = 'LTCG'
            else:
                h['tax_type'] = 'STCG'
        else:
            h['holding_years'] = 0
            h['tax_type'] = 'Unknown'
    
    return holdings

def score_stocks(holdings: List[Dict], fundamentals: Dict[str, Dict]) -> List[Dict]:
    """
    Score each stock based on fundamentals using stock_metrics logic.
    """
    for h in holdings:
        symbol = h['symbol']
        if symbol in fundamentals:
            fund = fundamentals[symbol]
            
            # Use existing stock_metrics scoring
            score_data = calculate_stock_score(fund)
            h['fundamental_score'] = score_data.get('score', 0)
            h['fundamental_grade'] = score_data.get('grade', 'N/A')
            h['fundamental_reasons'] = score_data.get('reasons', [])
            
            # Add fundamentals to holding
            h.update({
                'pe_ratio': fund.get('pe_ratio'),
                'pb_ratio': fund.get('pb_ratio'),
                'roe': fund.get('roe'),
                'debt_to_equity': fund.get('debt_to_equity'),
                'market_cap': fund.get('market_cap'),
                'sector': fund.get('sector'),
                'industry': fund.get('industry'),
                'dividend_yield': fund.get('dividend_yield')
            })
    
    return holdings

def generate_stock_recommendations(holdings: List[Dict], fundamentals: Dict[str, Dict]) -> Dict:
    """
    Generate stock recommendations based on:
    1. Current holdings analysis (buy more, hold, sell)
    2. Screener-based picks from existing screener.py
    """
    recommendations = {
        'holdings_advice': [],
        'new_picks': [],
        'sector_allocation': {},
        'alerts': []
    }
    
    # 1. Analyze current holdings
    for h in holdings:
        symbol = h['symbol']
        advice = {
            'symbol': symbol,
            'action': 'Hold',
            'reason': '',
            'current_price': h.get('current_price', 0),
            'return_pct': h.get('return_pct', 0)
        }
        
        if symbol in fundamentals:
            fund = fundamentals[symbol]
            score = h.get('fundamental_score', 0)
            
            # Sell signals
            if fund.get('pe_ratio') and fund['pe_ratio'] > 80:
                advice['action'] = 'Consider Selling'
                advice['reason'] = f"Very high P/E of {fund['pe_ratio']:.1f} - potentially overvalued"
            elif fund.get('debt_to_equity') and fund['debt_to_equity'] > 200:
                advice['action'] = 'Monitor Closely'
                advice['reason'] = f"High debt-to-equity of {fund['debt_to_equity']:.1f}%"
            elif h.get('return_pct', 0) < -30:
                advice['action'] = 'Review'
                advice['reason'] = f"Down {h['return_pct']:.1f}% - check if fundamentals have deteriorated"
            
            # Buy more signals
            elif score >= 75:
                advice['action'] = 'Buy More'
                advice['reason'] = f"Strong fundamentals (score: {score}/100)"
            elif fund.get('pe_ratio') and fund['pe_ratio'] < 15 and fund.get('roe') and fund['roe'] > 15:
                advice['action'] = 'Accumulate'
                advice['reason'] = f"Undervalued (P/E: {fund['pe_ratio']:.1f}, ROE: {fund['roe']:.1f}%)"
            
            else:
                advice['reason'] = f"Fundamental score: {score}/100"
        
        recommendations['holdings_advice'].append(advice)
    
    # 2. Get new stock picks from screener
    try:
        screened = screen_stocks(limit=10)
        if screened:
            for stock in screened:
                recommendations['new_picks'].append({
                    'symbol': stock.get('symbol'),
                    'name': stock.get('name', stock.get('symbol')),
                    'score': stock.get('score', 0),
                    'reason': stock.get('reason', ''),
                    'sector': stock.get('sector', 'Unknown'),
                    'pe': stock.get('pe_ratio'),
                    'roe': stock.get('roe')
                })
    except Exception as e:
        pass
    
    # 3. Calculate sector allocation
    sector_alloc = {}
    total_value = sum(h.get('current_value', 0) for h in holdings)
    
    for h in holdings:
        sector = h.get('sector', 'Unknown')
        value = h.get('current_value', 0)
        sector_alloc[sector] = sector_alloc.get(sector, 0) + value
    
    for sector, value in sector_alloc.items():
        pct = round((value / total_value * 100), 1) if total_value > 0 else 0
        recommendations['sector_allocation'][sector] = {
            'value': round(value, 2),
            'pct': pct
        }
    
    # 4. Generate alerts
    # Concentration risk
    if holdings:
        max_holding = max(holdings, key=lambda x: x.get('current_value', 0))
        max_pct = (max_holding.get('current_value', 0) / total_value * 100) if total_value > 0 else 0
        if max_pct > 25:
            recommendations['alerts'].append({
                'type': 'concentration',
                'severity': 'high',
                'message': f"{max_holding['symbol']} is {max_pct:.1f}% of portfolio. Consider diversifying."
            })
    
    # Sector concentration
    for sector, data in recommendations['sector_allocation'].items():
        if data['pct'] > 40:
            recommendations['alerts'].append({
                'type': 'sector',
                'severity': 'medium',
                'message': f"{sector} sector is {data['pct']:.1f}% of portfolio. Consider rebalancing."
            })
    
    return recommendations

def analyze_stock_portfolio(raw: bytes, filename: str) -> Dict:
    """
    Main entry point: Parse stock holdings, fetch fundamentals, calculate returns,
    score stocks, and generate recommendations.
    """
    # 1. Parse holdings
    holdings = parse_stock_holdings_from_excel(raw, filename)
    if not holdings:
        return {'error': 'No valid stock holdings found in file'}
    
    # 2. Fetch fundamentals
    symbols = [h['symbol'] for h in holdings]
    fundamentals = fetch_stock_fundamentals(symbols)
    
    # 3. Calculate returns
    holdings = calculate_stock_returns(holdings, fundamentals)
    
    # 4. Score stocks
    holdings = score_stocks(holdings, fundamentals)
    
    # 5. Generate recommendations
    recommendations = generate_stock_recommendations(holdings, fundamentals)
    
    # 6. Calculate portfolio summary
    total_invested = sum(h.get('invested', 0) for h in holdings)
    total_value = sum(h.get('current_value', 0) for h in holdings)
    total_gain = total_value - total_invested
    overall_return = round((total_gain / total_invested * 100), 2) if total_invested > 0 else 0
    
    # 7. Tax loss harvesting for stocks
    harvest_candidates = []
    for h in holdings:
        if h.get('gain', 0) < 0:
            harvest_candidates.append({
                'symbol': h['symbol'],
                'loss': abs(h['gain']),
                'tax_type': h.get('tax_type', 'Unknown'),
                'holding_years': h.get('holding_years', 0),
                'action': f"Book loss of ₹{abs(h['gain']):,.0f} to set off against gains"
            })
    
    harvest_candidates.sort(key=lambda x: x['loss'], reverse=True)
    
    return {
        'summary': {
            'total_stocks': len(holdings),
            'total_invested': round(total_invested, 2),
            'total_value': round(total_value, 2),
            'total_gain': round(total_gain, 2),
            'overall_return_pct': overall_return
        },
        'holdings': holdings,
        'recommendations': recommendations,
        'tax_harvest': harvest_candidates
    }