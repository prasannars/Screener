import { Search, BarChart3 } from 'lucide-react';
import { cn, SectionTitle, DataTable, SortableTh, LoadMore, EmptyState, SkeletonTable } from './ui';

export default function AllStocksTab({
  allStocks, stocksLoading, stocksError, stocksPagination, stocksSortBy, stocksSortDir,
  onSortStocks, stocksSector, setStocksSector, stocksSectors, stocksQuery, setStocksQuery, fetchAllStocks, onStockClick
}) {
  const sectors = stocksSectors?.length ? stocksSectors : [];
  return (
    <div>
      <SectionTitle icon={BarChart3} color="text-indigo-600" title="All Indian Stocks" subtitle="Tap any stock for full details" />
      
      <div className="bg-white p-4 rounded-2xl border border-slate-200 shadow-sm mb-4 md:mb-6">
        <div className="flex flex-col md:flex-row gap-3">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400 w-4 h-4" />
            <input type="search" value={stocksQuery} onChange={(e) => setStocksQuery(e.target.value)}
              onKeyDown={(e) => { if (e.key === 'Enter') fetchAllStocks(0); }}
              placeholder="Search symbol or name"
              className="w-full pl-10 pr-3 py-2.5 bg-slate-50 border border-slate-200 rounded-xl focus:ring-2 focus:ring-indigo-500 outline-none text-sm" />
          </div>
          <select value={stocksSector} onChange={(e) => setStocksSector(e.target.value)}
            className="px-3 py-2.5 bg-slate-50 border border-slate-200 rounded-xl text-sm">
            <option value="">All Sectors</option>
            {sectors.map((s) => <option key={s} value={s}>{s}</option>)}
          </select>
          <button onClick={() => fetchAllStocks(0)} className="px-5 py-2.5 bg-indigo-600 text-white rounded-xl text-sm font-semibold hover:bg-indigo-700">
            Search
          </button>
        </div>
      </div>

      <p className="text-xs md:text-sm text-slate-500 mb-3">
        Showing {allStocks.length.toLocaleString('en-IN')} of {(stocksPagination.total || 0).toLocaleString('en-IN')} stocks
      </p>
      {stocksError && <p className="text-sm text-red-600 mb-3">{stocksError}</p>}

      {stocksLoading && allStocks.length === 0 ? <SkeletonTable /> : allStocks.length === 0 ? (
        <EmptyState text="No stocks match those filters." />
      ) : (
        <>
          <DataTable>
            <thead className="bg-slate-50 border-b border-slate-200">
              <tr>
                <SortableTh label="Symbol" sortKey="symbol" current={stocksSortBy} dir={stocksSortDir} onSort={onSortStocks} />
                <SortableTh label="Price" sortKey="price" current={stocksSortBy} dir={stocksSortDir} onSort={onSortStocks} />
                <SortableTh label="P/E" sortKey="pe" current={stocksSortBy} dir={stocksSortDir} onSort={onSortStocks} />
                <SortableTh label="ROE" sortKey="roe" current={stocksSortBy} dir={stocksSortDir} onSort={onSortStocks} />
                <SortableTh label="Score" sortKey="score" current={stocksSortBy} dir={stocksSortDir} onSort={onSortStocks} />
                <SortableTh label="Sector" sortKey="sector" current={stocksSortBy} dir={stocksSortDir} onSort={onSortStocks} />
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {allStocks.map((s) => (
                <tr key={s.symbol} className="hover:bg-indigo-50/50 cursor-pointer transition-colors" onClick={() => onStockClick(s.symbol)}>
                  <td className="px-3 md:px-6 py-3">
                    <p className="text-sm font-bold text-slate-900">{s.symbol}</p>
                    <p className="text-[10px] text-slate-500 truncate max-w-[120px]">{s.name}</p>
                  </td>
                  <td className="px-3 md:px-6 py-3 text-sm font-medium">{s.current_price != null ? `₹${Number(s.current_price).toLocaleString('en-IN')}` : '—'}</td>
                  <td className="px-3 md:px-6 py-3 text-sm text-slate-600">{s.pe_ratio ?? '—'}</td>
                  <td className="px-3 md:px-6 py-3 text-sm text-slate-600">{s.roe ?? '—'}</td>
                  <td className="px-3 md:px-6 py-3 text-sm font-semibold text-indigo-600">{s.score ?? '—'}</td>
                  <td className="px-3 md:px-6 py-3 text-xs text-slate-500 hidden md:table-cell">{s.sector || '—'}</td>
                </tr>
              ))}
            </tbody>
          </DataTable>
          {stocksPagination?.has_more && (
            <LoadMore onClick={() => fetchAllStocks(allStocks.length)} loading={stocksLoading} remaining={stocksPagination.total - allStocks.length} />
          )}
        </>
      )}
    </div>
  );
}