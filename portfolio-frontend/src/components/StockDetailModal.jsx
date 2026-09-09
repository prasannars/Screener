import { useState, useEffect } from 'react';
import { X, ArrowLeft, TrendingUp, TrendingDown, Brain, Star } from 'lucide-react';
import { cn, Badge, MetricRow } from './ui';

import { cn, Badge, MetricRow } from './ui';
import { API } from '../api';

export default function StockDetailModal({ symbol, onClose }) {
  const [details, setDetails] = useState(null);
  const [loading, setLoading] = useState(true);
  const [aiInsight, setAiInsight] = useState(null);
  const [aiLoading, setAiLoading] = useState(false);

  useEffect(() => {
    fetch(`${API}/api/stocks/${symbol}/details`)
      .then(r => r.json())
      .then(data => { setDetails(data.data); setLoading(false); })
      .catch(() => setLoading(false));
  }, [symbol]);

  const fetchAI = async () => {
    setAiLoading(true);
    try {
      const res = await fetch(`${API}/api/ai/stock-insight/${symbol}`);
      const data = await res.json();
      setAiInsight(data.insight || 'No insight available.');
    } catch {
      setAiInsight('Failed. Is Ollama running?');
    } finally {
      setAiLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-[100] flex items-end md:items-center justify-center">
      <div className="absolute inset-0 bg-black/50 backdrop-blur-sm" onClick={onClose} />
      <div className="relative bg-white w-full md:max-w-2xl md:rounded-2xl rounded-t-3xl max-h-[90vh] overflow-y-auto shadow-2xl">
        {/* Header */}
        <div className="sticky top-0 bg-white border-b border-slate-100 px-4 md:px-6 py-4 flex items-center justify-between z-10">
          <div className="flex items-center gap-3">
            <button onClick={onClose} className="p-2 hover:bg-slate-100 rounded-lg md:hidden">
              <ArrowLeft className="w-5 h-5" />
            </button>
            <button onClick={onClose} className="p-2 hover:bg-slate-100 rounded-lg hidden md:block">
              <X className="w-5 h-5" />
            </button>
            <div>
              <h2 className="text-lg font-bold text-slate-900">{details?.basic?.name || symbol}</h2>
              <p className="text-xs text-slate-500">{details?.basic?.sector || 'Loading...'}</p>
            </div>
          </div>
          {details?.basic?.current_price && (
            <div className="text-right">
              <p className="text-xl font-bold text-slate-900">₹{Number(details.basic.current_price).toLocaleString('en-IN', { minimumFractionDigits: 2 })}</p>
            </div>
          )}
        </div>

        {loading ? (
          <div className="p-6 space-y-4 animate-pulse">
            <div className="h-8 bg-slate-200 rounded w-2/3" />
            <div className="h-32 bg-slate-100 rounded-xl" />
            <div className="h-32 bg-slate-100 rounded-xl" />
          </div>
        ) : details ? (
          <div className="p-4 md:p-6 space-y-6">
            {/* Score Card */}
            <div className={cn(
              'p-4 rounded-xl border',
              (details.score?.fundamental_score || 0) >= 70 ? 'bg-emerald-50 border-emerald-200' :
              (details.score?.fundamental_score || 0) >= 50 ? 'bg-amber-50 border-amber-200' :
              'bg-red-50 border-red-200'
            )}>
              <div className="flex items-center justify-between mb-2">
                <span className="text-sm font-semibold text-slate-700">Fundamental Score</span>
                <span className={cn(
                  'text-2xl font-bold',
                  (details.score?.fundamental_score || 0) >= 70 ? 'text-emerald-700' :
                  (details.score?.fundamental_score || 0) >= 50 ? 'text-amber-700' : 'text-red-700'
                )}>
                  {details.score?.fundamental_score || '—'}/100
                </span>
              </div>
              <div className="flex items-center gap-2">
                <Badge color={details.score?.grade === 'A' ? 'green' : details.score?.grade === 'B' ? 'blue' : 'amber'}>
                  Grade: {details.score?.grade || '—'}
                </Badge>
              </div>
              {details.score?.reasons?.length > 0 && (
                <ul className="mt-3 space-y-1">
                  {details.score.reasons.map((r, i) => (
                    <li key={i} className="text-xs text-slate-600 flex items-start gap-1.5">
                      <span className="w-1.5 h-1.5 rounded-full bg-slate-400 mt-1.5 flex-shrink-0" />
                      {r}
                    </li>
                  ))}
                </ul>
              )}
            </div>

            {/* AI Insight */}
            <div className="bg-indigo-50 border border-indigo-100 rounded-xl p-4">
              <button
                onClick={fetchAI}
                disabled={aiLoading}
                className="flex items-center gap-2 text-sm font-semibold text-indigo-700 hover:text-indigo-800"
              >
                <Brain className="w-4 h-4" />
                {aiLoading ? 'AI is analyzing...' : aiInsight ? 'Refresh AI Insight' : 'Get AI Analysis'}
              </button>
              {aiInsight && (
                <p className="mt-3 text-sm text-slate-700 italic leading-relaxed">"{aiInsight}"</p>
              )}
            </div>

            {/* Fundamentals Grid */}
            <div>
              <h3 className="font-bold text-slate-900 mb-3">Fundamentals</h3>
              <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
                {[
                  { label: 'P/E Ratio', value: details.fundamentals?.pe_ratio },
                  { label: 'P/B Ratio', value: details.fundamentals?.pb_ratio },
                  { label: 'ROE', value: details.fundamentals?.roe != null ? `${(details.fundamentals.roe < 1 ? details.fundamentals.roe * 100 : details.fundamentals.roe).toFixed(1)}%` : '—' },
                  { label: 'Debt/Equity', value: details.fundamentals?.debt_to_equity },
                  { label: 'Profit Margin', value: details.fundamentals?.profit_margin != null ? `${(details.fundamentals.profit_margin < 1 ? details.fundamentals.profit_margin * 100 : details.fundamentals.profit_margin).toFixed(1)}%` : '—' },
                  { label: 'Revenue Growth', value: details.fundamentals?.revenue_growth != null ? `${(details.fundamentals.revenue_growth < 1 ? details.fundamentals.revenue_growth * 100 : details.fundamentals.revenue_growth).toFixed(1)}%` : '—' },
                  { label: 'Dividend Yield', value: details.fundamentals?.dividend_yield != null ? `${(details.fundamentals.dividend_yield < 1 ? details.fundamentals.dividend_yield * 100 : details.fundamentals.dividend_yield).toFixed(2)}%` : '—' },
                  { label: 'Market Cap', value: details.basic?.market_cap ? `₹${(details.basic.market_cap / 1e7).toFixed(0)} Cr` : '—' },
                  { label: '52W High', value: details.valuation?.['52w_high'] ? `₹${Number(details.valuation['52w_high']).toLocaleString('en-IN')}` : '—' },
                  { label: '52W Low', value: details.valuation?.['52w_low'] ? `₹${Number(details.valuation['52w_low']).toLocaleString('en-IN')}` : '—' },
                ].map((item, i) => (
                  <div key={i} className="bg-slate-50 p-3 rounded-xl">
                    <p className="text-[10px] md:text-xs text-slate-500 mb-1">{item.label}</p>
                    <p className="text-sm font-bold text-slate-900">{item.value ?? '—'}</p>
                  </div>
                ))}
              </div>
            </div>

            {/* Peers */}
            {details.peers?.length > 0 && (
              <div>
                <h3 className="font-bold text-slate-900 mb-3">Sector Peers</h3>
                <div className="space-y-2">
                  {details.peers.map((peer) => (
                    <div key={peer.symbol} className="flex justify-between items-center p-3 bg-slate-50 rounded-xl">
                      <div>
                        <p className="text-sm font-semibold text-slate-900">{peer.symbol}</p>
                        <p className="text-xs text-slate-500">Score: {peer.score ?? '—'}</p>
                      </div>
                      <div className="text-right">
                        <p className="text-sm font-medium">₹{peer.current_price != null ? Number(peer.current_price).toLocaleString('en-IN') : '—'}</p>
                        <p className="text-xs text-slate-500">P/E: {peer.pe_ratio ?? '—'}</p>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        ) : (
          <div className="p-6 text-center text-slate-500">Failed to load stock details.</div>
        )}
      </div>
    </div>
  );
}