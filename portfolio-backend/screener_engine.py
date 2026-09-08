"""
Grouped Screener: Returns recommendations grouped by strategy/category.
"""
from typing import List, Dict
import mutual_funds # Your existing AMFI fetcher
from stock_metrics import calculate_stock_score, get_fundamentals # Your existing metrics

STOCK_UNIVERSE = [
    'RELIANCE', 'TCS', 'HDFCBANK', 'INFY', 'ICICIBANK', 'HINDUNILVR', 'ITC', 
    'SBIN', 'BHARTIARTL', 'KOTAKBANK', 'LT', 'AXISBANK', 'ASIANPAINT', 'MARUTI', 
    'SUNPHARMA', 'TITAN', 'BAJFINANCE', 'WIPRO', 'ULTRACEMCO', 'NESTLEIND', 
    'HCLTECH', 'POWERGRID', 'NTPC', 'ONGC', 'TATAMOTORS', 'M&M', 'JSWSTEEL', 
    'TATASTEEL', 'COALINDIA', 'DRREDDY', 'CIPLA', 'GRASIM', 'TECHM', 'DIVISLAB'
]

def get_grouped_stock_recommendations() -> Dict[str, List[Dict]]:
    """Group stocks into Value, Growth, Momentum, and Dividend strategies."""
    grouped = {"Value Picks": [], "Growth Picks": [], "Dividend Kings": []}
    
    for symbol in STOCK_UNIVERSE:
        fund = get_fundamentals(symbol)
        if not fund or not fund.get('current_price'):
            continue
            
        score_data = calculate_stock_score(fund)
        pe = fund.get('pe_ratio') or 999
        roe = (fund.get('roe') or 0) * 100 if (fund.get('roe') or 0) < 1 else (fund.get('roe') or 0)
        debt = fund.get('debt_to_equity') or 999
        div_yield = (fund.get('dividend_yield') or 0) * 100 if (fund.get('dividend_yield') or 0) < 1 else (fund.get('dividend_yield') or 0)
        
        stock_data = {
            'symbol': symbol,
            'price': fund.get('current_price'),
            'pe': round(pe, 1) if pe else None,
            'roe': round(roe, 1) if roe else None,
            'score': score_data.get('score'),
            'sector': fund.get('sector')
        }
        
        if pe < 25 and roe > 12 and debt < 100:
            grouped["Value Picks"].append(stock_data)
        if roe > 18 and score_data.get('score', 0) > 70:
            grouped["Growth Picks"].append(stock_data)
        if div_yield > 3.0:
            grouped["Dividend Kings"].append({**stock_data, 'div_yield': round(div_yield, 2)})

    for name, group in grouped.items():
        group.sort(key=lambda x: x.get('score') or 0, reverse=True)
        grouped[name] = group[:5]
        
    return grouped

def get_grouped_mf_recommendations() -> Dict[str, List[Dict]]:
    """Group Mutual Funds by SEBI Category: Large Cap, Mid Cap, Small Cap, Flexi Cap, Debt."""
    funds_data = mutual_funds.get_funds(refresh=False)
    rows = funds_data.get("rows", [])
    direct_growth = [r for r in rows if r.get('plan') == 'Direct' and r.get('option') == 'Growth']
    
    grouped = {"Large Cap": [], "Mid Cap": [], "Small Cap": [], "Flexi Cap": [], "Debt": []}
    category_map = {
        "large cap": "Large Cap", "mid cap": "Mid Cap", "small cap": "Small Cap",
        "flexi cap": "Flexi Cap", "multi cap": "Flexi Cap", "debt": "Debt", 
        "liquid": "Debt", "short duration": "Debt"
    }
    
    for fund in direct_growth:
        cat = fund.get('category', '').lower()
        target_group = next((val for key, val in category_map.items() if key in cat), None)
        
        if target_group and fund.get('ret_1y') is not None:
            grouped[target_group].append({
                'name': fund.get('name'),
                'amc': fund.get('amc'),
                'ret_1y': round(fund.get('ret_1y'), 2),
                'ret_3y': round(fund.get('ret_3y'), 2) if fund.get('ret_3y') else None,
                'ai_score': round(fund.get('ai_score', 0.5), 2),
                'code': fund.get('code')
            })
            
    for name, group in grouped.items():
        group.sort(key=lambda x: x.get('ai_score') or 0, reverse=True)
        grouped[name] = group[:3]
        
    return grouped