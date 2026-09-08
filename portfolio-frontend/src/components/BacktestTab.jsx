import { RefreshCw, Filter } from 'lucide-react';
import { cn, SectionTitle, DataTable } from './ui';

export default function BacktestTab({
  backtestSymbols,
  setBacktestSymbols,
  runBacktest,
  isBacktesting,
  backtestResults,
}) {
  return (
    <div className="max-w-4xl mx-auto">
      <SectionTitle icon={RefreshCw} color="text-indigo-600" title="Strategy Backtester" subtitle="50/200 SMA crossover over 3 years" />
      <div className="bg-white p-4 md:p-6 rounded-2xl border border-slate-200 shadow-sm mb-6 md:mb-8">
        <label className="block text-sm font-semibold text-slate-700 mb-2">Stock symbols (comma-separated)</label>
        <div className="flex flex-col sm:flex-row gap-3">
          <input
            type="text"
            value={backtestSymbols}
            onChange={(e) => setBacktestSymbols(e.target.value)}
            className="flex-1 px-4 py-3 bg-slate-50 border border-slate-200 rounded-xl focus:ring-2 focus:ring-indigo-500 outline-none text-sm"
            placeholder="RELIANCE,TCS,HDFCBANK"
          />
          <button
            onClick={runBacktest}
            disabled={isBacktesting}
            className="px-6 py-3 bg-indigo-600 text-white rounded-xl hover:bg-indigo-700 disabled:opacity-50 font-semibold flex items-center justify-center gap-2 text-sm"
          >
            <RefreshCw className={cn('w-4 h-4', isBacktesting && 'animate-spin')} />
            {isBacktesting ? 'Running...' : 'Run Backtest'}
          </button>
        </div>
        <p className="text-xs text-slate-500 mt-3 flex items-center gap-1">
          <Filter className="w-3 h-3" /> Default strategy: 50/200 SMA crossover over 3 years.
        </p>
      </div>
      {backtestResults && (
        <DataTable>
          <thead className="bg-slate-50 border-b border-slate-200">
            <tr>
              {['Symbol', 'Total Return', 'Sharpe Ratio', 'Max Drawdown', 'Win Rate'].map((header) => (
                <th key={header} className="px-6 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wider text-left">{header}</th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {(backtestResults.results || []).map((res, idx) => (
              <tr key={idx} className="hover:bg-slate-50/80">
                <td className="px-6 py-4 font-bold text-slate-900">{res.symbol}</td>
                <td className={cn('px-6 py-4 font-bold', res.total_return_pct >= 0 ? 'text-emerald-600' : 'text-red-600')}>{res.total_return_pct}%</td>
                <td className="px-6 py-4 text-slate-700">{res.sharpe_ratio}</td>
                <td className="px-6 py-4 text-red-600">{res.max_drawdown_pct}%</td>
                <td className="px-6 py-4 text-slate-700">{res.win_rate_pct}%</td>
              </tr>
            ))}
          </tbody>
        </DataTable>
      )}
    </div>
  );
}
