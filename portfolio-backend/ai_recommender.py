"""
Local AI Recommender using Ollama (Qwen 2.5).
Generates plain-English reasoning for stock and mutual fund recommendations.
"""
import ollama

def generate_stock_insight(symbol: str, fundamentals: dict) -> str:
    """Generate AI insight for a stock based on its fundamentals."""
    pe = fundamentals.get('pe_ratio', 'N/A')
    roe = fundamentals.get('roe', 'N/A')
    debt = fundamentals.get('debt_to_equity', 'N/A')
    sector = fundamentals.get('sector', 'N/A')
    
    prompt = f"""You are an expert Indian equity research analyst. 
    Analyze this stock: {symbol}
    Fundamentals: P/E: {pe}, ROE: {roe}%, Debt/Equity: {debt}%, Sector: {sector}
    Provide a concise, 2-sentence recommendation. 
    Sentence 1: Why it's a good/bad pick based on these numbers.
    Sentence 2: One key risk to watch.
    Keep it under 50 words. Do not use markdown."""
    
    try:
        response = ollama.chat(model='qwen2.5:7b', messages=[{'role': 'user', 'content': prompt}])
        return response['message']['content'].strip()
    except Exception as e:
        return f"AI insight unavailable (Ensure Ollama is running): {str(e)}"

def generate_mf_insight(fund_name: str, category: str, ret_1y: float, ret_3y: float, ai_score: float) -> str:
    """Generate AI insight for a mutual fund."""
    prompt = f"""You are an expert Indian mutual fund analyst.
    Fund: {fund_name} ({category})
    Returns: 1Y: {ret_1y}%, 3Y: {ret_3y}%, AI Quality Score: {ai_score}/1.0
    Provide a concise, 2-sentence recommendation.
    Sentence 1: Assessment of its consistency and category performance.
    Sentence 2: Who this fund is suitable for (e.g., aggressive, conservative).
    Keep it under 50 words. Do not use markdown."""
    
    try:
        response = ollama.chat(model='qwen2.5:7b', messages=[{'role': 'user', 'content': prompt}])
        return response['message']['content'].strip()
    except Exception as e:
        return f"AI insight unavailable: {str(e)}"