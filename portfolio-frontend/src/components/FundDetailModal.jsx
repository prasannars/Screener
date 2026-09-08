import { useState, useEffect } from 'react';
import { X, ArrowLeft, Brain, TrendingUp, Shield, Info } from 'lucide-react';
import { cn, Badge, MetricRow, fmtPct } from './ui';

const API = 'http://localhost:8000';

export default function FundDetailModal({ code, onClose }) {
  const [details, setDetails] = useState(null);
  const [loading, setLoading] = useState(true);
  const [aiInsight, setAiInsight] = useState(null);
  const [aiLoading, setAiLoading] = useState(false);

  useEffect(() => {
    fetch(`${API}/api/mutual-funds/${code}/details`)
      .then(r => r.json())
      .then(data => { setDetails(data.data); setLoading(false); })
      .catch(() => setLoading(false));
  }, [code]);

  const fetchAI = async () => {
    setAiLoading(true);
    try {
      const res = await fetch(`${API}/api/ai/mf-insight/${code}`);
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
              <h2 className="text-sm md:text-lg font-bold text-slate-900 leading-tight">{details?.basic?.name || 'Loading...'}</h2>
              <p className="text-xs text-slate-500">{details?.basic?.amc} • {details?.basic?.category}</p>
            </div>
          </div>
          {details?.basic?.nav && (
            <div className="text-right">
              <p className="text-lg font-bold text-slate-900">₹{Number(details.basic.nav).toFixed(4)}</p>
              <p className="text-[10px] text-slate-400">NAV</p>
            </div>
          )}
        </div>

        {loading ? (
          <div className="p-6 space-y-4 animate-pulse">
            <div className="h-8 bg-slate-200 rounded w-2/3" />
            <div className="h-32 bg-slate-100 rounded-xl" />
          </div>
        ) : details ? (
          <div className="p-4 md:p-6 space-y-6">
            {/* AI Score */}
            <div className={cn(
              'p-4 rounded-xl border flex items-center justify-between',
              (details.ai_score || 0) >= 0.7 ? 'bg-emerald-50 border-emerald-200' :
              (details.ai_score || 0) >= 0.5 ? 'bg-amber-50 border-amber-200' :
              'bg-red-50 border-red-200'
            )}>
              <div>
                <p className="text-sm font-semibold text-slate-700">AI Quality Score</p>
                <p className="text-xs text-slate-500 mt-0.5">{details.quality || 'Based on returns & risk'}</p>
              </div>
              <span className={cn(
                'text-3xl font-bold',
                (details.ai_score || 0) >= 0.7 ? 'text-emerald-700' :
                (details.ai_score || 0) >= 0.5 ? 'text-amber-700' : 'text-red-700'
              )}>
                {details.ai_score?.toFixed(2) || '—'}
              </span>
            </div>

            {/* AI Insight */}
            <div className="bg-indigo-50 border border-indigo-100 rounded-xl p-4">
              <button onClick={fetchAI} disabled={aiLoading} className="flex items-center gap-2 text-sm font-semibold text-indigo-700">
                <Brain className="w-4 h-4" />
                {aiLoading ? 'AI is analyzing...' : aiInsight ? 'Refresh Insight' : 'Get AI Analysis'}
              </button>
              {aiInsight && <p className="mt-3 text-sm text-slate-700 italic leading-relaxed">"{aiInsight}"</p>}
            </div>

            {/* Returns */}
            <div>
              <h3 className="font-bold text-slate-900 mb-3 flex items-center gap-2">
                <TrendingUp className="w-4 h-4 text-emerald-600" /> Returns
              </h3>
              <div className="grid grid-cols-3 md:grid-cols-6 gap-2">
                {[
                  { label: '1M', value: details.returns?.ret_1m },
                  { label: '3M', value: details.returns?.ret_3m },
                  { label: '6M', value: details.returns?.ret_6m },
                  { label: '1Y', value: details.returns?.ret_1y },
                  { label: '3Y', value: details.returns?.ret_3y },
                  { label: '5Y', value: details.returns?.ret_5y },
                ].map((item, i) => (
                  <div key={i} className="bg-slate-50 p-3 rounded-xl text-center">
                    <p className="text-[10px] text-slate-500 mb-1">{item.label}</p>
                    <p className={cn('text-sm font-bold', (item.value || 0) >= 0 ? 'text-emerald-700' : 'text-red-700')}>
                      {item.value != null ? `${item.value > 0 ? '+' : ''}${item.value.toFixed(1)}%` : '—'}
                    </p>
                  </div>
                ))}
              </div>
            </div>

            {/* Risk Metrics */}
            <div>
              <h3 className="font-bold text-slate-900 mb-3 flex items-center gap-2">
                <Shield className="w-4 h-4 text-blue-600" /> Risk Metrics
              </h3>
              <div className="bg-white border border-slate-200 rounded-xl p-4">
                <MetricRow label="Volatility (1Y)" value={details.risk_metrics?.vol_1y != null ? `${details.risk_metrics.vol_1y.toFixed(2)}%` : '—'} />
                <MetricRow label="Max Drawdown (1Y)" value={details.risk_metrics?.max_dd_1y != null ? `${details.risk_metrics.max_dd_1y.toFixed(2)}%` : '—'} highlight="text-red-600" />
                <MetricRow label="Sharpe Ratio (1Y)" value={details.risk_metrics?.sharpe_1y != null ? details.risk_metrics.sharpe_1y.toFixed(2) : '—'} />
                <MetricRow label="Beta" value={details.risk_metrics?.beta ?? '—'} />
                <MetricRow label="Alpha" value={details.risk_metrics?.alpha ?? '—'} />
              </div>
            </div>

            {/* Fund Info */}
            <div>
              <h3 className="font-bold text-slate-900 mb-3 flex items-center gap-2">
                <Info className="w-4 h-4 text-slate-500" /> Fund Details
              </h3>
              <div className="bg-white border border-slate-200 rounded-xl p-4">
                <MetricRow label="AMC" value={details.basic?.amc || '—'} />
                <MetricRow label="Category" value={details.basic?.category || '—'} />
                <MetricRow label="Plan" value={details.basic?.plan || '—'} />
                <MetricRow label="Option" value={details.basic?.option || '—'} />
                <MetricRow label="NAV Date" value={details.basic?.nav_date || '—'} />
              </div>
            </div>
          </div>
        ) : (
          <div className="p-6 text-center text-slate-500">Failed to load fund details.</div>
        )}
      </div>
    </div>
  );
}