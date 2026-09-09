import { TrendingUp, BarChart3, AlertCircle, Brain, Wallet, FileText, Upload, Lock } from 'lucide-react';
import { cn, SectionTitle, SummaryCard } from './ui';

export default function PortfolioTab({
  handleMFUpload, handleStockUpload, isAnalyzing, error,
  casPassword, setCasPassword, stockPassword, setStockPassword,
}) {
  return (
    <div>
      <SectionTitle icon={Upload} color="text-indigo-600" title="Upload" subtitle="A new CAS replaces saved funds. A new stock file replaces saved stocks. The other sleeve stays as-is." />

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 md:gap-6">
          <div className="bg-white border border-slate-200 rounded-2xl p-6 md:p-8 text-center hover:shadow-md hover:border-indigo-200 transition-all">
            <div className="mx-auto w-14 h-14 rounded-xl bg-indigo-50 flex items-center justify-center mb-4">
              <FileText className="text-indigo-600 w-7 h-7" />
            </div>
            <p className="text-base md:text-lg font-semibold text-slate-900">Mutual Fund CAS PDF</p>
            <p className="text-xs md:text-sm text-slate-500 mt-1 mb-4">Reads mutual fund schemes only from CAMS, KFintech, NSDL, or CDSL</p>
            <div className="relative mb-3 text-left">
              <Lock className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400 w-4 h-4" />
              <input
                type="password"
                value={casPassword || ''}
                onChange={(e) => setCasPassword(e.target.value)}
                placeholder="PAN or PDF password"
                autoComplete="off"
                className="w-full pl-10 pr-3 py-2.5 bg-slate-50 border border-slate-200 rounded-xl text-sm outline-none focus:ring-2 focus:ring-indigo-500"
              />
            </div>
            <p className="text-[11px] text-slate-400 mb-4">Required for most CAS PDFs. Leave blank if unlocked.</p>
            <label className="inline-flex px-5 py-2.5 bg-indigo-600 text-white text-sm font-semibold rounded-xl hover:bg-indigo-700 transition-colors cursor-pointer">
              {isAnalyzing ? 'Analyzing...' : 'Choose PDF'}
              <input type="file" accept=".pdf" className="hidden" onChange={handleMFUpload} disabled={isAnalyzing} />
            </label>
          </div>
          <div className="bg-white border border-slate-200 rounded-2xl p-6 md:p-8 text-center hover:shadow-md hover:border-emerald-200 transition-all">
            <div className="mx-auto w-14 h-14 rounded-xl bg-emerald-50 flex items-center justify-center mb-4">
              <BarChart3 className="text-emerald-600 w-7 h-7" />
            </div>
            <p className="text-base md:text-lg font-semibold text-slate-900">Stock Portfolio</p>
            <p className="text-xs md:text-sm text-slate-500 mt-1 mb-4">Reads equities only from Excel/CSV or an NSDL/CDSL CAS PDF</p>
            <div className="relative mb-3 text-left">
              <Lock className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400 w-4 h-4" />
              <input
                type="password"
                value={stockPassword || ''}
                onChange={(e) => setStockPassword(e.target.value)}
                placeholder="PAN or file password"
                autoComplete="off"
                className="w-full pl-10 pr-3 py-2.5 bg-slate-50 border border-slate-200 rounded-xl text-sm outline-none focus:ring-2 focus:ring-emerald-500"
              />
            </div>
            <p className="text-[11px] text-slate-400 mb-4">Only needed if the workbook is password-protected.</p>
            <label className="inline-flex px-5 py-2.5 bg-emerald-600 text-white text-sm font-semibold rounded-xl hover:bg-emerald-700 transition-colors cursor-pointer">
              {isAnalyzing ? 'Analyzing...' : 'Choose Excel or PDF'}
              <input type="file" accept=".xlsx,.xls,.csv,.pdf" className="hidden" onChange={handleStockUpload} disabled={isAnalyzing} />
            </label>
          </div>
        </div>

      {error && (
        <div className="mt-4 p-4 bg-red-50 border border-red-200 rounded-xl flex gap-3 items-start">
          <AlertCircle className="text-red-600 w-5 h-5 flex-shrink-0 mt-0.5" />
          <p className="text-sm text-red-800">{error}</p>
        </div>
      )}
    </div>
  );
}

function MFDashboard({ report }) {
  const summary = report.summary || {};
  const holdings = report.holdings || [];
  const actions = report.verdict?.actions || [];
  const taxHarvest = report.tax_harvest || [];
  const invested = Number(summary.invested) || holdings.reduce((s, h) => s + Number(h.invested || 0), 0);
  const value = Number(summary.value) || holdings.reduce((s, h) => s + Number(h.value || 0), 0);
  const gain = summary.gain != null ? Number(summary.gain) : (invested ? value - invested : null);
  const retPct = summary.ret_pct != null ? Number(summary.ret_pct) : (invested && gain != null ? (gain / invested) * 100 : null);
  const isPositive = (gain || 0) >= 0;
  const hasCost = invested > 0 && gain != null;

  return (
    <div className="space-y-4 md:space-y-6 mt-6">
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 md:gap-4">
        <SummaryCard title="Invested" value={invested} subtitle={`${summary.funds || holdings.length} schemes`} />
        <SummaryCard title="Current Value" value={value} subtitle={summary.xirr != null ? `XIRR: ${summary.xirr}%` : 'XIRR: N/A'} />
        <div className={cn('p-4 md:p-6 rounded-2xl border shadow-sm', hasCost ? (isPositive ? 'bg-emerald-50 border-emerald-100' : 'bg-red-50 border-red-100') : 'bg-white border-slate-200')}>
          <p className="text-xs md:text-sm font-medium text-slate-600 mb-1">Total Returns</p>
          {hasCost ? (
            <>
              <p className={cn('text-xl md:text-3xl font-bold', isPositive ? 'text-emerald-700' : 'text-red-700')}>
                {isPositive ? '+' : ''}₹{Number(gain).toLocaleString('en-IN')}
              </p>
              <p className="text-xs md:text-sm font-semibold mt-1">{isPositive ? '+' : ''}{Number(retPct).toFixed(2)}%</p>
            </>
          ) : (
            <>
              <p className="text-xl md:text-3xl font-bold text-slate-400">—</p>
              <p className="text-xs text-slate-500 mt-1">Purchase cost missing in this statement</p>
            </>
          )}
        </div>
      </div>

      {taxHarvest.length > 0 && (
        <div className="bg-indigo-50 border border-indigo-200 rounded-2xl p-4 md:p-6">
          <div className="flex items-center gap-3 mb-4">
            <div className="p-2 bg-indigo-100 rounded-lg"><Wallet className="w-5 h-5 text-indigo-600" /></div>
            <div>
              <h3 className="text-sm md:text-lg font-bold text-indigo-900">Tax Loss Harvesting</h3>
              <p className="text-xs md:text-sm text-indigo-700">Book losses to reduce your tax liability.</p>
            </div>
          </div>
          <div className="space-y-2">
            {taxHarvest.slice(0, 3).map((item, idx) => (
              <div key={idx} className="bg-white p-3 rounded-lg border border-indigo-100 flex justify-between items-center">
                <div>
                  <p className="font-semibold text-gray-900 text-xs md:text-sm">{item.name}</p>
                  <p className="text-[10px] md:text-xs text-gray-500">{item.tax_type} Loss</p>
                </div>
                <p className="font-bold text-red-600 text-sm">-₹{item.loss.toLocaleString('en-IN')}</p>
              </div>
            ))}
          </div>
        </div>
      )}

      {actions.length > 0 && (
        <div className="bg-white p-4 md:p-6 rounded-2xl border border-slate-200 space-y-3">
          <h3 className="font-semibold text-slate-900 flex items-center gap-2 text-sm md:text-base"><Brain className="w-4 h-4 text-purple-600" /> AI Insights</h3>
          {actions.slice(0, 4).map((a, i) => (
            <p key={i} className="text-xs md:text-sm text-amber-800 bg-amber-50 border border-amber-100 rounded-xl p-3 flex gap-2">
              <AlertCircle className="w-4 h-4 flex-shrink-0 mt-0.5" /> {a}
            </p>
          ))}
        </div>
      )}

      <div className="bg-white p-4 md:p-6 rounded-2xl border border-slate-200">
        <h3 className="font-semibold text-slate-900 mb-4 text-sm md:text-base">
          Holdings ({holdings.length})
        </h3>
        {holdings.length === 0 ? (
          <p className="text-sm text-slate-500">No mutual fund schemes found in this file.</p>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3 max-h-[36rem] overflow-y-auto pr-1">
            {holdings.map((h, i) => {
              const hPos = (h.gain || 0) >= 0;
              return (
                <div key={`${h.name}-${h.amfi_code || i}`} className="p-3 md:p-4 rounded-xl border border-slate-100 bg-slate-50/50">
                  <div className="flex justify-between items-start mb-2">
                    <p className="font-semibold text-xs md:text-sm text-slate-900 leading-tight">{h.name}</p>
                    <span className={cn('text-[10px] md:text-xs font-bold px-2 py-1 rounded-md', h.ret_pct == null ? 'bg-slate-100 text-slate-500' : hPos ? 'bg-emerald-100 text-emerald-700' : 'bg-red-100 text-red-700')}>
                      {h.ret_pct == null ? '—' : `${hPos ? '+' : ''}${h.ret_pct}%`}
                    </span>
                  </div>
                  <div className="flex justify-between text-xs md:text-sm mt-2">
                    <span className="text-slate-500">₹{(h.invested || 0).toLocaleString('en-IN')}</span>
                    <span className="font-medium text-slate-900">₹{(h.value || 0).toLocaleString('en-IN')}</span>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}

function StockDashboard({ report }) {
  const summary = report.summary || {};
  const holdings = report.holdings || [];
  const alerts = report.recommendations?.alerts || [];
  const taxHarvest = report.tax_harvest || [];
  const isPositive = (summary.total_gain || 0) >= 0;

  return (
    <div className="space-y-4 md:space-y-6 mt-6">
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 md:gap-4">
        <SummaryCard title="Invested" value={summary.total_invested} subtitle={`${summary.total_stocks || holdings.length} stocks`} />
        <SummaryCard title="Current Value" value={summary.total_value} subtitle={`${isPositive ? '+' : ''}${summary.overall_return_pct}%`} />
        <div className={cn('p-4 md:p-6 rounded-2xl border', isPositive ? 'bg-emerald-50 border-emerald-100' : 'bg-red-50 border-red-100')}>
          <p className="text-xs md:text-sm font-medium text-slate-600 mb-1">Total Gain</p>
          <p className={cn('text-xl md:text-3xl font-bold', isPositive ? 'text-emerald-700' : 'text-red-700')}>₹{(summary.total_gain || 0).toLocaleString('en-IN')}</p>
        </div>
      </div>

      {taxHarvest.length > 0 && (
        <div className="bg-indigo-50 border border-indigo-200 rounded-2xl p-4 md:p-6">
          <div className="flex items-center gap-3 mb-4">
            <div className="p-2 bg-indigo-100 rounded-lg"><Wallet className="w-5 h-5 text-indigo-600" /></div>
            <h3 className="text-sm md:text-lg font-bold text-indigo-900">Tax Loss Harvesting</h3>
          </div>
          <div className="space-y-2">
            {taxHarvest.slice(0, 3).map((item, idx) => (
              <div key={idx} className="bg-white p-3 rounded-lg border border-indigo-100 flex justify-between items-center">
                <div>
                  <p className="font-semibold text-gray-900 text-xs md:text-sm">{item.symbol}</p>
                  <p className="text-[10px] md:text-xs text-gray-500">{item.tax_type}</p>
                </div>
                <p className="font-bold text-red-600 text-sm">-₹{item.loss.toLocaleString('en-IN')}</p>
              </div>
            ))}
          </div>
        </div>
      )}

      {alerts.map((a, i) => (
        <p key={i} className="text-xs md:text-sm text-red-800 bg-red-50 border border-red-100 rounded-xl p-3 flex gap-2">
          <AlertCircle className="w-4 h-4 flex-shrink-0 mt-0.5" /> {a.message}
        </p>
      ))}

      <div className="bg-white p-4 md:p-6 rounded-2xl border border-slate-200">
        <h3 className="font-semibold text-slate-900 mb-4 text-sm md:text-base">Your Stock Holdings ({holdings.length})</h3>
        {holdings.length === 0 ? (
          <p className="text-sm text-slate-500">No equity holdings found in this file.</p>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3 max-h-[36rem] overflow-y-auto pr-1">
            {holdings.map((h, i) => {
              const isPos = (h.gain || 0) >= 0;
              return (
                <div key={`${h.symbol}-${i}`} className="p-3 md:p-4 rounded-xl border border-slate-100 bg-slate-50/50">
                  <div className="flex justify-between items-start mb-2">
                    <div>
                      <p className="font-semibold text-slate-900 text-xs md:text-sm">{h.symbol}</p>
                      <p className="text-[10px] md:text-xs text-slate-500">{h.sector || h.name || '—'} • Score: {h.fundamental_score || 'N/A'}/100</p>
                    </div>
                    <span className={cn('text-xs md:text-sm font-bold', isPos ? 'text-emerald-700' : 'text-red-700')}>
                      {isPos ? '+' : ''}{h.return_pct ?? h.ret_pct}%
                    </span>
                  </div>
                  <div className="flex justify-between mt-2 pt-2 border-t border-slate-100 text-xs md:text-sm text-slate-600">
                    <span>₹{(h.invested || 0).toLocaleString('en-IN')}</span>
                    <span className="font-medium text-slate-900">₹{(h.current_value || h.value || 0).toLocaleString('en-IN')}</span>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}