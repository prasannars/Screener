import { X, ArrowLeft } from 'lucide-react';
import { cn, fmtPct, fmtNum } from './ui';

export default function FundCompare({ data, onClose }) {
  if (!data || data.length === 0) return null;

  const metrics = [
    { key: 'nav', label: 'NAV', format: (v) => v != null ? `₹${Number(v).toFixed(4)}` : '—' },
    { key: 'ret_1y', label: '1Y Return', format: (v) => v != null ? `${v > 0 ? '+' : ''}${v.toFixed(2)}%` : '—', color: true },
    { key: 'ret_3y', label: '3Y Return', format: (v) => v != null ? `${v > 0 ? '+' : ''}${v.toFixed(2)}%` : '—', color: true },
    { key: 'ret_5y', label: '5Y Return', format: (v) => v != null ? `${v > 0 ? '+' : ''}${v.toFixed(2)}%` : '—', color: true },
    { key: 'vol_1y', label: 'Volatility (1Y)', format: (v) => v != null ? `${v.toFixed(2)}%` : '—' },
    { key: 'sharpe_1y', label: 'Sharpe Ratio', format: (v) => v != null ? v.toFixed(2) : '—' },
    { key: 'max_dd_1y', label: 'Max Drawdown', format: (v) => v != null ? `${v.toFixed(2)}%` : '—', color: true, invert: true },
    { key: 'ai_score', label: 'AI Score', format: (v) => v != null ? v.toFixed(2) : '—' },
  ];

  // Find best value for each metric
  const bestValues = {};
  metrics.forEach(m => {
    const values = data.map(d => d[m.key]).filter(v => v != null);
    if (values.length > 0) {
      bestValues[m.key] = m.invert ? Math.min(...values) : Math.max(...values);
    }
  });

  return (
    <div className="fixed inset-0 z-[100] flex items-end md:items-center justify-center">
      <div className="absolute inset-0 bg-black/50 backdrop-blur-sm" onClick={onClose} />
      <div className="relative bg-white w-full md:max-w-4xl md:rounded-2xl rounded-t-3xl max-h-[90vh] overflow-y-auto shadow-2xl">
        <div className="sticky top-0 bg-white border-b border-slate-100 px-4 md:px-6 py-4 flex items-center justify-between z-10">
          <div className="flex items-center gap-3">
            <button onClick={onClose} className="p-2 hover:bg-slate-100 rounded-lg">
              <ArrowLeft className="w-5 h-5" />
            </button>
            <h2 className="text-lg font-bold text-slate-900">Fund Comparison</h2>
          </div>
          <button onClick={onClose} className="p-2 hover:bg-slate-100 rounded-lg">
            <X className="w-5 h-5" />
          </button>
        </div>

        <div className="p-4 md:p-6 overflow-x-auto">
          <table className="w-full min-w-[500px]">
            <thead>
              <tr>
                <th className="text-left text-xs font-semibold text-slate-500 uppercase py-3 pr-4 w-32">Metric</th>
                {data.map((fund) => (
                  <th key={fund.code} className="text-left py-3 px-2">
                    <p className="text-xs md:text-sm font-bold text-slate-900 leading-tight">{fund.name}</p>
                    <p className="text-[10px] text-slate-500">{fund.amc}</p>
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              <tr className="border-t border-slate-100">
                <td className="py-3 pr-4 text-xs text-slate-500 font-medium">Category</td>
                {data.map((fund) => (
                  <td key={fund.code} className="py-3 px-2 text-xs text-slate-700">{fund.category || '—'}</td>
                ))}
              </tr>
              {metrics.map((metric) => (
                <tr key={metric.key} className="border-t border-slate-50">
                  <td className="py-3 pr-4 text-xs text-slate-500 font-medium">{metric.label}</td>
                  {data.map((fund) => {
                    const val = fund[metric.key];
                    const isBest = val != null && val === bestValues[metric.key] && data.length > 1;
                    return (
                      <td key={fund.code} className="py-3 px-2">
                        <span className={cn(
                          'text-xs md:text-sm font-semibold',
                          isBest && 'text-emerald-700 bg-emerald-50 px-1.5 py-0.5 rounded',
                          metric.color && !isBest && val != null && (metric.invert ? val > 0 : val < 0) ? 'text-red-600' :
                          metric.color && !isBest && val != null && (metric.invert ? val <= 0 : val >= 0) ? 'text-emerald-700' :
                          'text-slate-900'
                        )}>
                          {metric.format(val)}
                          {isBest && ' ★'}
                        </span>
                      </td>
                    );
                  })}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}