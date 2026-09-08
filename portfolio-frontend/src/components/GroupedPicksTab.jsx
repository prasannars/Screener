import { Search, TrendingUp, PieChart, BarChart3, Brain, CheckCircle, AlertCircle } from 'lucide-react';
import { cn, SectionTitle, SkeletonGrid } from './ui';

export default function GroupedPicksTab({ groupedMFs, groupedStocks, groupedLoading, picksQuery, setPicksQuery, aiInsights, fetchAiInsight, onStockClick, onFundClick }) {
  const q = picksQuery.trim().toLowerCase();
  const filterFunds = (funds) => (Array.isArray(funds) ? funds : []).filter((f) => !q || (f.name || '').toLowerCase().includes(q));
  const filterStocks = (stocks) => (Array.isArray(stocks) ? stocks : []).filter((s) => !q || (s.symbol || '').toLowerCase().includes(q));

  return (
    <div className="space-y-6 md:space-y-8">
      <SectionTitle icon={TrendingUp} color="text-indigo-600" title="Smart Picks" subtitle="Pro investment themes & top funds by category" />

      <div className="relative max-w-md">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400 w-5 h-5" />
        <input type="text" placeholder="Search..." value={picksQuery} onChange={(e) => setPicksQuery(e.target.value)}
          className="w-full pl-10 pr-4 py-3 bg-white border border-slate-200 rounded-xl focus:ring-2 focus:ring-indigo-500 outline-none shadow-sm text-sm" />
      </div>

      {/* Mutual Funds */}
      <section>
        <div className="flex items-center gap-2 mb-4">
          <PieChart className="text-purple-600 w-5 h-5" />
          <h3 className="text-lg md:text-xl font-bold text-slate-900">Top Funds by Category</h3>
        </div>
        {groupedLoading ? <SkeletonGrid count={3} /> : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 md:gap-6">
            {Object.entries(groupedMFs).map(([category, funds]) => (
              <div key={category} className="bg-white p-4 md:p-5 rounded-2xl border border-slate-200 shadow-sm">
                <div className="flex justify-between items-center mb-3">
                  <h4 className="font-bold text-base text-slate-800">{category}</h4>
                  <span className="text-[10px] font-semibold bg-purple-50 text-purple-700 px-2 py-0.5 rounded-full border border-purple-100">Direct • Growth</span>
                </div>
                <div className="space-y-2">
                  {filterFunds(funds).map((fund, idx) => (
                    <div key={idx} className="p-3 bg-slate-50 rounded-xl border border-slate-100 cursor-pointer hover:border-indigo-200 transition-colors" onClick={() => onFundClick(fund.code)}>
                      <div className="flex justify-between items-start mb-1 gap-2">
                        <p className="font-semibold text-xs md:text-sm text-slate-900 leading-tight">{fund.name}</p>
                        <span className="text-[10px] font-bold text-emerald-600 bg-emerald-50 px-1.5 py-0.5 rounded">{fund.ai_score}</span>
                      </div>
                      <div className="flex gap-3 text-[10px] md:text-xs text-slate-600">
                        <span>1Y: <b className="text-slate-900">{fund.ret_1y}%</b></span>
                        {fund.ret_3y && <span>3Y: <b className="text-slate-900">{fund.ret_3y}%</b></span>}
                        {fund.ret_5y && <span>5Y: <b className="text-slate-900">{fund.ret_5y}%</b></span>}
                      </div>
                      <button onClick={(e) => { e.stopPropagation(); fetchAiInsight('mf', fund.code); }}
                        className="mt-2 w-full flex items-center justify-center gap-1.5 text-[10px] md:text-xs font-medium text-indigo-600 bg-indigo-50 hover:bg-indigo-100 py-1.5 rounded-lg">
                        {aiInsights[fund.code] === 'loading' ? <span className="animate-pulse">Thinking...</span> : aiInsights[fund.code] ? <CheckCircle className="w-3 h-3" /> : <Brain className="w-3 h-3" />}
                        {aiInsights[fund.code] && aiInsights[fund.code] !== 'loading' ? 'Done' : 'Ask AI'}
                      </button>
                      {aiInsights[fund.code] && aiInsights[fund.code] !== 'loading' && (
                        <p className="mt-2 text-[10px] md:text-xs text-slate-700 italic bg-white p-2 rounded-lg border border-indigo-100">"{aiInsights[fund.code]}"</p>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </div>
        )}
      </section>

      {/* Stock Themes */}
      <section>
        <div className="flex items-center gap-2 mb-4">
          <BarChart3 className="text-blue-600 w-5 h-5" />
          <h3 className="text-lg md:text-xl font-bold text-slate-900">Stock Investment Themes</h3>
        </div>
        {groupedLoading ? <SkeletonGrid count={4} /> : (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 md:gap-6">
            {Object.entries(groupedStocks).map(([theme, stocks]) => {
              const isRed = theme.includes("Red Flags");
              return (
                <div key={theme} className={cn("bg-white p-4 md:p-5 rounded-2xl border shadow-sm", isRed ? "border-red-200 bg-red-50/30" : "border-slate-200")}>
                  <h4 className={cn("font-bold text-base mb-3 flex items-center gap-2", isRed ? "text-red-700" : "text-blue-700")}>
                    {isRed && <AlertCircle className="w-4 h-4" />}{theme}
                  </h4>
                  <div className="space-y-2">
                    {filterStocks(stocks).map((stock, idx) => (
                      <div key={idx} onClick={() => onStockClick(stock.symbol)}
                        className="flex justify-between items-center p-3 bg-white rounded-xl border border-slate-100 hover:border-blue-200 transition-colors cursor-pointer">
                        <div>
                          <p className="font-bold text-slate-900 text-xs md:text-sm">{stock.symbol}</p>
                          <p className="text-[10px] md:text-xs text-blue-600 font-medium">{stock.theme_reason}</p>
                        </div>
                        <div className="text-right">
                          <p className="font-semibold text-xs md:text-sm text-slate-900">₹{stock.price != null ? Number(stock.price).toLocaleString('en-IN') : '—'}</p>
                          <p className="text-[10px] text-slate-500">Score: {stock.score}</p>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </section>
    </div>
  );
}