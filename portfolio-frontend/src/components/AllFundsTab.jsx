import { Search, PieChart, GitCompareArrows, X } from 'lucide-react';
import { cn, SectionTitle, DataTable, SortableTh, LoadMore, EmptyState, SkeletonTable, fmtNav, fmtPct } from './ui';

export default function AllFundsTab({
  allFunds, fundsLoading, fundsError, fundsPagination, fundsSortBy, fundsSortDir, onSortFunds,
  fundsCategory, setFundsCategory, fundsBucket, setFundsBucket, fundsQuery, setFundsQuery,
  mfCategories, fetchAllFunds, onFundClick, compareMode, setCompareMode, selectedForCompare, toggleCompare, runComparison, comparisonData, setComparisonData
}) {
  return (
    <div>
      <SectionTitle icon={PieChart} color="text-indigo-600" title="All Mutual Funds" subtitle="Tap any fund for details • Select to compare" />

      <div className="bg-white p-4 rounded-2xl border border-slate-200 shadow-sm mb-4 md:mb-6">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-3">
          <div className="relative md:col-span-2">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400 w-4 h-4" />
            <input type="search" value={fundsQuery} onChange={(e) => setFundsQuery(e.target.value)}
              onKeyDown={(e) => { if (e.key === 'Enter') fetchAllFunds(0); }}
              placeholder="Search fund or AMC"
              className="w-full pl-10 pr-3 py-2.5 bg-slate-50 border border-slate-200 rounded-xl focus:ring-2 focus:ring-indigo-500 outline-none text-sm" />
          </div>
          <select value={fundsCategory} onChange={(e) => setFundsCategory(e.target.value)} className="px-3 py-2.5 bg-slate-50 border border-slate-200 rounded-xl text-sm">
            <option value="">All Categories</option>
            {(mfCategories.categories || []).map((c) => <option key={c} value={c}>{c}</option>)}
          </select>
          <div className="flex gap-2">
            <button onClick={() => fetchAllFunds(0)} className="flex-1 px-4 py-2.5 bg-indigo-600 text-white rounded-xl text-sm font-semibold hover:bg-indigo-700">
              Search
            </button>
            <button onClick={() => setCompareMode(!compareMode)}
              className={cn('px-3 py-2.5 rounded-xl text-sm font-semibold border transition-colors', compareMode ? 'bg-purple-600 text-white border-purple-600' : 'bg-white text-slate-600 border-slate-200 hover:border-purple-300')}>
              <GitCompareArrows className="w-4 h-4" />
            </button>
          </div>
        </div>

        {/* Compare bar */}
        {compareMode && (
          <div className="mt-3 p-3 bg-purple-50 border border-purple-200 rounded-xl">
            <div className="flex flex-wrap items-center gap-2">
              <span className="text-xs font-semibold text-purple-700">Compare ({selectedForCompare.filter(s => s.type === 'fund').length}/4):</span>
              {selectedForCompare.filter(s => s.type === 'fund').map((item) => (
                <span key={item.id} className="inline-flex items-center gap-1 text-xs bg-white px-2 py-1 rounded-lg border border-purple-200">
                  {item.data?.name?.slice(0, 20) || item.id}...
                  <button onClick={() => toggleCompare(item.data, 'fund')}><X className="w-3 h-3 text-slate-400" /></button>
                </span>
              ))}
              {selectedForCompare.filter(s => s.type === 'fund').length >= 2 && (
                <button onClick={runComparison} className="ml-auto px-3 py-1.5 bg-purple-600 text-white text-xs font-semibold rounded-lg hover:bg-purple-700">
                  Compare Now
                </button>
              )}
            </div>
          </div>
        )}
      </div>

      <p className="text-xs md:text-sm text-slate-500 mb-3">
        Showing {allFunds.length.toLocaleString('en-IN')} of {(fundsPagination.total || 0).toLocaleString('en-IN')} schemes
      </p>
      {fundsError && <p className="text-sm text-red-600 mb-3">{fundsError}</p>}

      {fundsLoading && allFunds.length === 0 ? <SkeletonTable /> : allFunds.length === 0 ? (
        <EmptyState text="No funds match those filters." />
      ) : (
        <>
          <DataTable>
            <thead className="bg-slate-50 border-b border-slate-200">
              <tr>
                {compareMode && <th className="px-3 py-3 w-10"></th>}
                <SortableTh label="Fund" sortKey="name" current={fundsSortBy} dir={fundsSortDir} onSort={onSortFunds} />
                <SortableTh label="Category" sortKey="category" current={fundsSortBy} dir={fundsSortDir} onSort={onSortFunds} />
                <SortableTh label="NAV" sortKey="nav" current={fundsSortBy} dir={fundsSortDir} onSort={onSortFunds} />
                <SortableTh label="1Y" sortKey="ret_1y" current={fundsSortBy} dir={fundsSortDir} onSort={onSortFunds} />
                <SortableTh label="3Y" sortKey="ret_3y" current={fundsSortBy} dir={fundsSortDir} onSort={onSortFunds} />
                <SortableTh label="AI" sortKey="ai_score" current={fundsSortBy} dir={fundsSortDir} onSort={onSortFunds} />
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {allFunds.map((f) => (
                <tr key={f.code || f.name} className="hover:bg-indigo-50/50 cursor-pointer transition-colors" onClick={() => !compareMode && onFundClick(f.code)}>
                  {compareMode && (
                    <td className="px-3 py-3" onClick={(e) => { e.stopPropagation(); toggleCompare(f, 'fund'); }}>
                      <input type="checkbox" readOnly checked={!!selectedForCompare.find(s => s.id === f.code)}
                        className="w-4 h-4 rounded border-slate-300 text-purple-600 focus:ring-purple-500" />
                    </td>
                  )}
                  <td className="px-3 md:px-6 py-3">
                    <p className="text-xs md:text-sm font-medium text-slate-900 truncate max-w-[200px]">{f.name}</p>
                    <p className="text-[10px] text-slate-400">{f.amc}</p>
                  </td>
                  <td className="px-3 md:px-6 py-3 text-xs text-slate-500 hidden md:table-cell">{f.category || f.bucket || '—'}</td>
                  <td className="px-3 md:px-6 py-3 text-xs md:text-sm text-slate-700">{fmtNav(f.nav)}</td>
                  <td className="px-3 md:px-6 py-3 text-xs md:text-sm">{fmtPct(f.ret_1y)}</td>
                  <td className="px-3 md:px-6 py-3 text-xs md:text-sm">{fmtPct(f.ret_3y)}</td>
                  <td className="px-3 md:px-6 py-3 text-xs md:text-sm font-semibold text-indigo-600">{f.ai_score != null ? f.ai_score.toFixed(2) : '—'}</td>
                </tr>
              ))}
            </tbody>
          </DataTable>
          {fundsPagination?.has_more && (
            <LoadMore onClick={() => fetchAllFunds(allFunds.length)} loading={fundsLoading} remaining={fundsPagination.total - allFunds.length} />
          )}
        </>
      )}
    </div>
  );
}