import { useState, useEffect } from 'react';
import {
  TrendingUp, Brain, Activity, BarChart3, RefreshCw, Search,
  Filter, PieChart, CheckCircle, AlertCircle, Upload, ChevronUp, ChevronDown,
} from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

const API = 'http://localhost:8000';

const TABS = [
  { id: 'portfolio', label: 'Portfolio', icon: Upload },
  { id: 'stocks', label: 'All Stocks', icon: BarChart3 },
  { id: 'funds', label: 'All Funds', icon: PieChart },
  { id: 'grouped', label: 'Smart Picks', icon: TrendingUp },
  { id: 'live', label: 'Live Market', icon: Activity },
  { id: 'backtest', label: 'Backtest', icon: RefreshCw },
];

function cn(...classes) {
  return classes.filter(Boolean).join(' ');
}

function App() {
  const [activeTab, setActiveTab] = useState('portfolio');
  const [portfolioSubTab, setPortfolioSubTab] = useState('upload');
  const [mfReport, setMfReport] = useState(null);
  const [stockReport, setStockReport] = useState(null);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [error, setError] = useState('');

  const [allStocks, setAllStocks] = useState([]);
  const [stocksLoading, setStocksLoading] = useState(false);
  const [stocksPagination, setStocksPagination] = useState({ total: 0, has_more: false });
  const [stocksSortBy, setStocksSortBy] = useState('name');
  const [stocksSortDir, setStocksSortDir] = useState('asc');
  const [stocksSector, setStocksSector] = useState('');
  const [stocksSectors, setStocksSectors] = useState([]);
  const [stocksError, setStocksError] = useState('');
  const [stocksQuery, setStocksQuery] = useState('');

  const [allFunds, setAllFunds] = useState([]);
  const [fundsLoading, setFundsLoading] = useState(false);
  const [fundsPagination, setFundsPagination] = useState({ total: 0, has_more: false });
  const [fundsSortBy, setFundsSortBy] = useState('name');
  const [fundsSortDir, setFundsSortDir] = useState('asc');
  const [fundsCategory, setFundsCategory] = useState('');
  const [fundsBucket, setFundsBucket] = useState('');
  const [mfCategories, setMfCategories] = useState({ categories: [], buckets: [] });
  const [fundsQuery, setFundsQuery] = useState('');
  const [fundsError, setFundsError] = useState('');

  const [groupedStocks, setGroupedStocks] = useState({});
  const [groupedMFs, setGroupedMFs] = useState({});
  const [groupedLoading, setGroupedLoading] = useState(false);
  const [picksQuery, setPicksQuery] = useState('');
  const [aiInsights, setAiInsights] = useState({});
  const [backtestSymbols, setBacktestSymbols] = useState('RELIANCE,TCS,HDFCBANK');
  const [backtestResults, setBacktestResults] = useState(null);
  const [isBacktesting, setIsBacktesting] = useState(false);

  useEffect(() => {
    if (activeTab === 'stocks' && allStocks.length === 0) fetchAllStocks(0);
  }, [activeTab]);

  useEffect(() => {
    if (activeTab !== 'funds') return;
    if (allFunds.length === 0) fetchAllFunds(0);
    fetchMfCategories();
  }, [activeTab]);

  useEffect(() => {
    if (activeTab !== 'grouped') return;
    setGroupedLoading(true);
    Promise.all([
      fetch(`${API}/api/recommendations/stocks`).then((r) => r.json()).catch(() => ({})),
      fetch(`${API}/api/recommendations/mutual-funds`).then((r) => r.json()).catch(() => ({})),
    ]).then(([stocks, funds]) => {
      setGroupedStocks(stocks.data || {});
      setGroupedMFs(funds.data || {});
    }).finally(() => setGroupedLoading(false));
  }, [activeTab]);

  const fetchAllStocks = async (offset = 0, overrides = {}) => {
    const sortBy = overrides.sortBy ?? stocksSortBy;
    const sortDir = overrides.sortDir ?? stocksSortDir;
    setStocksLoading(true);
    setStocksError('');
    try {
      let url = `${API}/api/stocks/all?limit=100&offset=${offset}&sort_by=${sortBy}&sort_dir=${sortDir}`;
      if (stocksSector) url += `&sector=${encodeURIComponent(stocksSector)}`;
      if (stocksQuery.trim()) url += `&q=${encodeURIComponent(stocksQuery.trim())}`;
      const response = await fetch(url);
      const result = await response.json();
      if (!response.ok || !result.success) throw new Error(result.detail || 'Failed to fetch stocks');
      setAllStocks(offset === 0 ? (result.data || []) : (prev) => [...prev, ...(result.data || [])]);
      setStocksPagination(result.pagination || { total: 0, has_more: false });
      if (Array.isArray(result.sectors) && result.sectors.length) setStocksSectors(result.sectors);
    } catch (err) {
      setStocksError(err.message || 'Failed to fetch stocks');
      if (offset === 0) setAllStocks([]);
    } finally {
      setStocksLoading(false);
    }
  };

  const fetchAllFunds = async (offset = 0, overrides = {}) => {
    const sortBy = overrides.sortBy ?? fundsSortBy;
    const sortDir = overrides.sortDir ?? fundsSortDir;
    setFundsLoading(true);
    setFundsError('');
    try {
      let url = `${API}/api/mutual-funds/all?limit=100&offset=${offset}&sort_by=${sortBy}&sort_dir=${sortDir}`;
      if (fundsCategory) url += `&category=${encodeURIComponent(fundsCategory)}`;
      if (fundsBucket) url += `&bucket=${encodeURIComponent(fundsBucket)}`;
      if (fundsQuery.trim()) url += `&q=${encodeURIComponent(fundsQuery.trim())}`;
      const response = await fetch(url);
      const result = await response.json();
      if (!response.ok || !result.success) throw new Error(result.detail || 'Failed to fetch funds');
      setAllFunds(offset === 0 ? (result.data || []) : (prev) => [...prev, ...(result.data || [])]);
      setFundsPagination(result.pagination || { total: 0, has_more: false });
    } catch (err) {
      setFundsError(err.message || 'Failed to fetch funds');
      if (offset === 0) setAllFunds([]);
    } finally {
      setFundsLoading(false);
    }
  };

  const fetchMfCategories = async () => {
    try {
      const response = await fetch(`${API}/api/mutual-funds/categories`);
      const result = await response.json();
      if (result.success) setMfCategories(result.data);
    } catch {
      /* keep previous filters */
    }
  };

  const handleMFUpload = async (event) => {
    const file = event.target.files[0];
    if (!file) return;
    setIsAnalyzing(true);
    setError('');
    const formData = new FormData();
    formData.append('file', file);
    formData.append('password', 'ABCDE1234F');
    try {
      const response = await fetch(`${API}/api/analyze-cas`, { method: 'POST', body: formData });
      if (!response.ok) {
        const errData = await response.json();
        throw new Error(errData.detail || 'Failed to analyze PDF');
      }
      const result = await response.json();
      setMfReport(result.data);
      setPortfolioSubTab('mf');
    } catch (err) {
      setError(err.message);
    } finally {
      setIsAnalyzing(false);
    }
  };

  const handleStockUpload = async (event) => {
    const file = event.target.files[0];
    if (!file) return;
    setIsAnalyzing(true);
    setError('');
    const formData = new FormData();
    formData.append('file', file);
    try {
      const response = await fetch(`${API}/api/analyze-stocks`, { method: 'POST', body: formData });
      if (!response.ok) {
        const errData = await response.json();
        throw new Error(errData.detail || 'Failed to analyze stocks');
      }
      const result = await response.json();
      setStockReport(result.data);
      setPortfolioSubTab('stocks');
    } catch (err) {
      setError(err.message);
    } finally {
      setIsAnalyzing(false);
    }
  };

  const fetchAiInsight = async (type, identifier) => {
    if (aiInsights[identifier] && aiInsights[identifier] !== 'loading') return;
    setAiInsights((prev) => ({ ...prev, [identifier]: 'loading' }));
    const endpoint = type === 'stock'
      ? `${API}/api/ai/stock-insight/${identifier}`
      : `${API}/api/ai/mf-insight/${identifier}`;
    try {
      const res = await fetch(endpoint);
      const data = await res.json();
      setAiInsights((prev) => ({ ...prev, [identifier]: data.insight || data.error || 'No insight available.' }));
    } catch {
      setAiInsights((prev) => ({ ...prev, [identifier]: 'Failed. Is Ollama running?' }));
    }
  };

  const runBacktest = async () => {
    setIsBacktesting(true);
    try {
      const res = await fetch(`${API}/api/backtest?symbols=${encodeURIComponent(backtestSymbols)}&years=3`);
      const data = await res.json();
      setBacktestResults(data.data);
    } finally {
      setIsBacktesting(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-50 text-slate-900">
      <nav className="bg-white/80 border-b border-slate-200 sticky top-0 z-50 backdrop-blur-md">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex flex-col xl:flex-row xl:items-center xl:justify-between gap-3 py-3">
            <div className="flex items-center gap-2">
              <div className="bg-indigo-600 p-2 rounded-lg">
                <Brain className="text-white w-5 h-5" />
              </div>
              <h1 className="text-xl font-bold bg-gradient-to-r from-indigo-600 to-purple-600 bg-clip-text text-transparent">
                PrasannaTrade AI
              </h1>
            </div>
            <div className="flex flex-wrap gap-1 bg-slate-100 p-1 rounded-xl">
              {TABS.map((tab) => (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id)}
                  className={cn(
                    'flex items-center gap-2 px-3 py-2 rounded-lg text-sm font-medium transition-all duration-200',
                    activeTab === tab.id
                      ? 'bg-white text-indigo-600 shadow-sm'
                      : 'text-slate-600 hover:text-slate-900 hover:bg-slate-200/50'
                  )}
                >
                  <tab.icon className="w-4 h-4" />
                  {tab.label}
                </button>
              ))}
            </div>
          </div>
        </div>
      </nav>

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <AnimatePresence mode="wait">
          {activeTab === 'portfolio' && (
            <TabPanel k="portfolio">
              <PortfolioTab
                portfolioSubTab={portfolioSubTab}
                setPortfolioSubTab={setPortfolioSubTab}
                mfReport={mfReport}
                stockReport={stockReport}
                handleMFUpload={handleMFUpload}
                handleStockUpload={handleStockUpload}
                isAnalyzing={isAnalyzing}
                error={error}
              />
            </TabPanel>
          )}

          {activeTab === 'stocks' && (
            <TabPanel k="stocks">
              <AllStocksTab
                allStocks={allStocks}
                stocksLoading={stocksLoading}
                stocksError={stocksError}
                stocksPagination={stocksPagination}
                stocksSortBy={stocksSortBy}
                stocksSortDir={stocksSortDir}
                onSortStocks={(key) => {
                  const defaults = { symbol: 'asc', name: 'asc', price: 'desc', pe: 'asc', roe: 'desc', score: 'desc', sector: 'asc' };
                  const nextDir = stocksSortBy === key ? (stocksSortDir === 'asc' ? 'desc' : 'asc') : (defaults[key] || 'asc');
                  setStocksSortBy(key);
                  setStocksSortDir(nextDir);
                  fetchAllStocks(0, { sortBy: key, sortDir: nextDir });
                }}
                stocksSector={stocksSector}
                setStocksSector={setStocksSector}
                stocksSectors={stocksSectors}
                stocksQuery={stocksQuery}
                setStocksQuery={setStocksQuery}
                fetchAllStocks={fetchAllStocks}
              />
            </TabPanel>
          )}

          {activeTab === 'funds' && (
            <TabPanel k="funds">
              <AllFundsTab
                allFunds={allFunds}
                fundsLoading={fundsLoading}
                fundsError={fundsError}
                fundsPagination={fundsPagination}
                fundsSortBy={fundsSortBy}
                fundsSortDir={fundsSortDir}
                onSortFunds={(key) => {
                  const defaults = { name: 'asc', category: 'asc', nav: 'desc', ret_1y: 'desc', ret_3y: 'desc', ai_score: 'desc' };
                  const nextDir = fundsSortBy === key ? (fundsSortDir === 'asc' ? 'desc' : 'asc') : (defaults[key] || 'asc');
                  setFundsSortBy(key);
                  setFundsSortDir(nextDir);
                  fetchAllFunds(0, { sortBy: key, sortDir: nextDir });
                }}
                fundsCategory={fundsCategory}
                setFundsCategory={setFundsCategory}
                fundsBucket={fundsBucket}
                setFundsBucket={setFundsBucket}
                fundsQuery={fundsQuery}
                setFundsQuery={setFundsQuery}
                mfCategories={mfCategories}
                fetchAllFunds={fetchAllFunds}
              />
            </TabPanel>
          )}

          {activeTab === 'grouped' && (
            <TabPanel k="grouped">
              <GroupedPicksTab
                groupedMFs={groupedMFs}
                groupedStocks={groupedStocks}
                groupedLoading={groupedLoading}
                picksQuery={picksQuery}
                setPicksQuery={setPicksQuery}
                aiInsights={aiInsights}
                fetchAiInsight={fetchAiInsight}
              />
            </TabPanel>
          )}

          {activeTab === 'live' && (
            <TabPanel k="live">
              <LiveMarketTab />
            </TabPanel>
          )}

          {activeTab === 'backtest' && (
            <TabPanel k="backtest">
              <BacktestTab
                backtestSymbols={backtestSymbols}
                setBacktestSymbols={setBacktestSymbols}
                runBacktest={runBacktest}
                isBacktesting={isBacktesting}
                backtestResults={backtestResults}
              />
            </TabPanel>
          )}
        </AnimatePresence>
      </main>
    </div>
  );
}

function TabPanel({ children, k }) {
  return (
    <motion.div
      key={k}
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -10 }}
      transition={{ duration: 0.2 }}
    >
      {children}
    </motion.div>
  );
}

function SectionTitle({ icon: Icon, color, title, subtitle }) {
  return (
    <div className="flex items-center gap-3 mb-6">
      <Icon className={cn('w-6 h-6', color)} />
      <div>
        <h2 className="text-2xl font-bold text-slate-900">{title}</h2>
        {subtitle && <p className="text-sm text-slate-500">{subtitle}</p>}
      </div>
    </div>
  );
}

function PortfolioTab({ portfolioSubTab, setPortfolioSubTab, mfReport, stockReport, handleMFUpload, handleStockUpload, isAnalyzing, error }) {
  return (
    <div>
      <SectionTitle icon={Upload} color="text-indigo-600" title="My Portfolio" subtitle="Import a CAS PDF or stock spreadsheet" />
      <div className="flex flex-wrap gap-1 bg-slate-100 p-1 rounded-xl w-fit mb-6">
        {[
          { id: 'upload', label: 'Upload', show: true },
          { id: 'mf', label: 'Mutual Funds', show: !!mfReport },
          { id: 'stocks', label: 'Stocks', show: !!stockReport },
        ].filter((t) => t.show).map((tab) => (
          <button
            key={tab.id}
            onClick={() => setPortfolioSubTab(tab.id)}
            className={cn(
              'px-4 py-2 rounded-lg text-sm font-medium transition-all',
              portfolioSubTab === tab.id ? 'bg-white text-indigo-600 shadow-sm' : 'text-slate-600 hover:bg-slate-200/50'
            )}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {portfolioSubTab === 'upload' && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <label className="bg-white border border-slate-200 rounded-2xl p-8 text-center hover:shadow-md hover:border-indigo-200 transition-all cursor-pointer">
            <div className="mx-auto w-12 h-12 rounded-xl bg-indigo-50 flex items-center justify-center mb-4">
              <TrendingUp className="text-indigo-600 w-6 h-6" />
            </div>
            <p className="text-lg font-semibold text-slate-900">Mutual Fund CAS PDF</p>
            <p className="text-sm text-slate-500 mt-1 mb-4">CAMS, KFintech, NSDL, or CDSL</p>
            <span className="inline-flex px-5 py-2.5 bg-indigo-600 text-white text-sm font-semibold rounded-xl">
              {isAnalyzing ? 'Analyzing...' : 'Choose PDF'}
            </span>
            <input type="file" accept=".pdf" className="hidden" onChange={handleMFUpload} disabled={isAnalyzing} />
          </label>
          <label className="bg-white border border-slate-200 rounded-2xl p-8 text-center hover:shadow-md hover:border-indigo-200 transition-all cursor-pointer">
            <div className="mx-auto w-12 h-12 rounded-xl bg-emerald-50 flex items-center justify-center mb-4">
              <BarChart3 className="text-emerald-600 w-6 h-6" />
            </div>
            <p className="text-lg font-semibold text-slate-900">Stock Portfolio Excel/CSV</p>
            <p className="text-sm text-slate-500 mt-1 mb-4">Columns: Symbol, Quantity, Buy Price, Buy Date</p>
            <span className="inline-flex px-5 py-2.5 bg-emerald-600 text-white text-sm font-semibold rounded-xl">
              {isAnalyzing ? 'Analyzing...' : 'Choose Excel/CSV'}
            </span>
            <input type="file" accept=".xlsx,.xls,.csv" className="hidden" onChange={handleStockUpload} disabled={isAnalyzing} />
          </label>
        </div>
      )}
      {error && (
        <div className="mt-4 p-4 bg-red-50 border border-red-200 rounded-xl flex gap-3 items-start">
          <AlertCircle className="text-red-600 w-5 h-5 flex-shrink-0 mt-0.5" />
          <p className="text-sm text-red-800">{error}</p>
        </div>
      )}
      {portfolioSubTab === 'mf' && mfReport && <MFDashboard report={mfReport} />}
      {portfolioSubTab === 'stocks' && stockReport && <StockDashboard report={stockReport} />}
    </div>
  );
}

function AllStocksTab({
  allStocks, stocksLoading, stocksError, stocksPagination, stocksSortBy, stocksSortDir,
  onSortStocks, stocksSector, setStocksSector, stocksSectors, stocksQuery, setStocksQuery, fetchAllStocks,
}) {
  const sectors = stocksSectors?.length ? stocksSectors : ['Technology', 'Financial Services', 'Healthcare', 'Energy', 'Consumer Cyclical'];
  return (
    <div>
      <SectionTitle icon={BarChart3} color="text-indigo-600" title="All Indian Stocks" subtitle="Search, filter, and sort the NSE listed universe" />
      <div className="bg-white p-4 rounded-2xl border border-slate-200 shadow-sm mb-6">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="md:col-span-2 relative">
            <Search className="absolute left-3 top-9 text-slate-400 w-4 h-4" />
            <label className="block text-sm font-semibold text-slate-700 mb-2">Search</label>
            <input
              type="search"
              value={stocksQuery}
              onChange={(e) => setStocksQuery(e.target.value)}
              onKeyDown={(e) => { if (e.key === 'Enter') fetchAllStocks(0); }}
              placeholder="Symbol or company name"
              className="w-full pl-10 pr-3 py-2.5 bg-slate-50 border border-slate-200 rounded-xl focus:ring-2 focus:ring-indigo-500 outline-none"
            />
          </div>
          <div>
            <label className="block text-sm font-semibold text-slate-700 mb-2">Sector</label>
            <select value={stocksSector} onChange={(e) => setStocksSector(e.target.value)} className="w-full px-3 py-2.5 bg-slate-50 border border-slate-200 rounded-xl">
              <option value="">All Sectors</option>
              {sectors.map((sector) => <option key={sector} value={sector}>{sector}</option>)}
            </select>
          </div>
        </div>
        <div className="mt-4">
          <button type="button" onClick={() => fetchAllStocks(0)} className="px-5 py-2.5 bg-indigo-600 text-white rounded-xl text-sm font-semibold hover:bg-indigo-700">
            Apply Filters
          </button>
        </div>
      </div>
      <p className="text-sm text-slate-500 mb-3">Showing {allStocks.length.toLocaleString('en-IN')} of {(stocksPagination.total || 0).toLocaleString('en-IN')} listed stocks</p>
      {stocksError && <p className="text-sm text-red-600 mb-3">{stocksError}</p>}
      {stocksLoading && allStocks.length === 0 ? <SkeletonTable /> : allStocks.length === 0 ? (
        <EmptyState text="No stocks match those filters." />
      ) : (
        <>
          <DataTable>
            <thead className="bg-slate-50 border-b border-slate-200">
              <tr>
                <SortableTh label="Symbol" sortKey="symbol" current={stocksSortBy} dir={stocksSortDir} onSort={onSortStocks} />
                <SortableTh label="Company" sortKey="name" current={stocksSortBy} dir={stocksSortDir} onSort={onSortStocks} />
                <SortableTh label="Price" sortKey="price" current={stocksSortBy} dir={stocksSortDir} onSort={onSortStocks} />
                <SortableTh label="P/E" sortKey="pe" current={stocksSortBy} dir={stocksSortDir} onSort={onSortStocks} />
                <SortableTh label="ROE" sortKey="roe" current={stocksSortBy} dir={stocksSortDir} onSort={onSortStocks} />
                <SortableTh label="Score" sortKey="score" current={stocksSortBy} dir={stocksSortDir} onSort={onSortStocks} />
                <SortableTh label="Sector" sortKey="sector" current={stocksSortBy} dir={stocksSortDir} onSort={onSortStocks} />
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {allStocks.map((s) => (
                <tr key={s.symbol} className="hover:bg-slate-50/80">
                  <td className="px-6 py-3 text-sm font-bold text-slate-900">{s.symbol}</td>
                  <td className="px-6 py-3 text-sm text-slate-600">{s.name}</td>
                  <td className="px-6 py-3 text-sm font-medium">{s.current_price != null ? `₹${Number(s.current_price).toLocaleString('en-IN')}` : '—'}</td>
                  <td className="px-6 py-3 text-sm text-slate-600">{s.pe_ratio ?? '—'}</td>
                  <td className="px-6 py-3 text-sm text-slate-600">{s.roe ?? '—'}</td>
                  <td className="px-6 py-3 text-sm font-semibold text-indigo-600">{s.score ?? '—'}</td>
                  <td className="px-6 py-3 text-sm text-slate-500">{s.sector || '—'}</td>
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

function AllFundsTab({
  allFunds, fundsLoading, fundsError, fundsPagination, fundsSortBy, fundsSortDir, onSortFunds,
  fundsCategory, setFundsCategory, fundsBucket, setFundsBucket, fundsQuery, setFundsQuery, mfCategories, fetchAllFunds,
}) {
  return (
    <div>
      <SectionTitle icon={PieChart} color="text-indigo-600" title="All Mutual Funds" subtitle="AMFI catalog with 1Y/3Y returns and AI scores" />
      <div className="bg-white p-4 rounded-2xl border border-slate-200 shadow-sm mb-6">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="relative">
            <Search className="absolute left-3 top-9 text-slate-400 w-4 h-4" />
            <label className="block text-sm font-semibold text-slate-700 mb-2">Search</label>
            <input
              type="search"
              value={fundsQuery}
              onChange={(e) => setFundsQuery(e.target.value)}
              onKeyDown={(e) => { if (e.key === 'Enter') fetchAllFunds(0); }}
              placeholder="Fund, AMC, or code"
              className="w-full pl-10 pr-3 py-2.5 bg-slate-50 border border-slate-200 rounded-xl focus:ring-2 focus:ring-indigo-500 outline-none"
            />
          </div>
          <div>
            <label className="block text-sm font-semibold text-slate-700 mb-2">Category</label>
            <select value={fundsCategory} onChange={(e) => setFundsCategory(e.target.value)} className="w-full px-3 py-2.5 bg-slate-50 border border-slate-200 rounded-xl">
              <option value="">All Categories</option>
              {(mfCategories.categories || []).map((c) => <option key={c} value={c}>{c}</option>)}
            </select>
          </div>
          <div>
            <label className="block text-sm font-semibold text-slate-700 mb-2">Bucket</label>
            <select value={fundsBucket} onChange={(e) => setFundsBucket(e.target.value)} className="w-full px-3 py-2.5 bg-slate-50 border border-slate-200 rounded-xl">
              <option value="">All Buckets</option>
              {(mfCategories.buckets || []).map((b) => <option key={b} value={b}>{b}</option>)}
            </select>
          </div>
        </div>
        <div className="mt-4">
          <button type="button" onClick={() => fetchAllFunds(0)} className="px-5 py-2.5 bg-indigo-600 text-white rounded-xl text-sm font-semibold hover:bg-indigo-700">
            Apply Filters
          </button>
        </div>
      </div>
      <p className="text-sm text-slate-500 mb-3">Showing {allFunds.length.toLocaleString('en-IN')} of {(fundsPagination.total || 0).toLocaleString('en-IN')} schemes</p>
      {fundsError && <p className="text-sm text-red-600 mb-3">{fundsError}</p>}
      {fundsLoading && allFunds.length === 0 ? <SkeletonTable /> : allFunds.length === 0 ? (
        <EmptyState text="No funds match those filters." />
      ) : (
        <>
          <DataTable>
            <thead className="bg-slate-50 border-b border-slate-200">
              <tr>
                <SortableTh label="Fund" sortKey="name" current={fundsSortBy} dir={fundsSortDir} onSort={onSortFunds} />
                <SortableTh label="Category" sortKey="category" current={fundsSortBy} dir={fundsSortDir} onSort={onSortFunds} />
                <SortableTh label="NAV" sortKey="nav" current={fundsSortBy} dir={fundsSortDir} onSort={onSortFunds} />
                <SortableTh label="1Y" sortKey="ret_1y" current={fundsSortBy} dir={fundsSortDir} onSort={onSortFunds} />
                <SortableTh label="3Y" sortKey="ret_3y" current={fundsSortBy} dir={fundsSortDir} onSort={onSortFunds} />
                <SortableTh label="AI Score" sortKey="ai_score" current={fundsSortBy} dir={fundsSortDir} onSort={onSortFunds} />
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {allFunds.map((f) => (
                <tr key={f.code || f.name} className="hover:bg-slate-50/80">
                  <td className="px-6 py-3 text-sm font-medium text-slate-900">{f.name}</td>
                  <td className="px-6 py-3 text-sm text-slate-500">{f.category || f.bucket || '—'}</td>
                  <td className="px-6 py-3 text-sm text-slate-700">{fmtNav(f.nav)}</td>
                  <td className="px-6 py-3 text-sm">{fmtPct(f.ret_1y)}</td>
                  <td className="px-6 py-3 text-sm">{fmtPct(f.ret_3y)}</td>
                  <td className="px-6 py-3 text-sm font-semibold text-indigo-600">{f.ai_score ?? '—'}</td>
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

function GroupedPicksTab({ groupedMFs, groupedStocks, groupedLoading, picksQuery, setPicksQuery, aiInsights, fetchAiInsight }) {
  const q = picksQuery.trim().toLowerCase();
  const filterFunds = (funds) => (Array.isArray(funds) ? funds : []).filter((f) => !q || (f.name || '').toLowerCase().includes(q));
  const filterStocks = (stocks) => (Array.isArray(stocks) ? stocks : []).filter((s) => !q || (s.symbol || '').toLowerCase().includes(q) || (s.sector || '').toLowerCase().includes(q));

  return (
    <div className="space-y-8">
      <SectionTitle icon={TrendingUp} color="text-indigo-600" title="Smart Picks" subtitle="Grouped recommendations from the screener" />
      <div className="relative max-w-md">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400 w-5 h-5" />
        <input
          type="text"
          placeholder="Search funds or stocks..."
          value={picksQuery}
          onChange={(e) => setPicksQuery(e.target.value)}
          className="w-full pl-10 pr-4 py-3 bg-white border border-slate-200 rounded-xl focus:ring-2 focus:ring-indigo-500 outline-none shadow-sm"
        />
      </div>

      <section>
        <div className="flex items-center gap-2 mb-4">
          <PieChart className="text-purple-600 w-5 h-5" />
          <h3 className="text-xl font-bold text-slate-900">Top Mutual Funds by Category</h3>
        </div>
        {groupedLoading ? <SkeletonGrid count={3} /> : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {Object.entries(groupedMFs).map(([category, funds]) => (
              <motion.div key={category} whileHover={{ y: -4 }} className="bg-white p-5 rounded-2xl border border-slate-200 shadow-sm">
                <div className="flex justify-between items-center mb-4">
                  <h4 className="font-bold text-lg text-slate-800">{category}</h4>
                  <span className="text-xs font-semibold bg-purple-50 text-purple-700 px-2.5 py-1 rounded-full border border-purple-100">Direct • Growth</span>
                </div>
                <div className="space-y-3">
                  {filterFunds(funds).map((fund, idx) => (
                    <div key={idx} className="p-3 bg-slate-50 rounded-xl border border-slate-100">
                      <div className="flex justify-between items-start mb-2 gap-2">
                        <p className="font-semibold text-sm text-slate-900 leading-tight">{fund.name}</p>
                        <span className="text-xs font-bold text-emerald-600 bg-emerald-50 px-2 py-1 rounded-md">{fund.ai_score}</span>
                      </div>
                      <div className="flex gap-4 text-xs text-slate-600 mb-3">
                        <span>1Y: <b className="text-slate-900">{fund.ret_1y}%</b></span>
                        {fund.ret_3y && <span>3Y: <b className="text-slate-900">{fund.ret_3y}%</b></span>}
                      </div>
                      <button onClick={() => fetchAiInsight('mf', fund.code)} className="w-full flex items-center justify-center gap-2 text-xs font-medium text-indigo-600 bg-indigo-50 hover:bg-indigo-100 py-2 rounded-lg">
                        {aiInsights[fund.code] === 'loading' ? <span className="animate-pulse">AI is thinking...</span> : aiInsights[fund.code] ? <CheckCircle className="w-3 h-3" /> : <Brain className="w-3 h-3" />}
                        {aiInsights[fund.code] && aiInsights[fund.code] !== 'loading' ? 'Insight Generated' : 'Ask AI Why'}
                      </button>
                      {aiInsights[fund.code] && aiInsights[fund.code] !== 'loading' && (
                        <p className="mt-3 text-xs text-slate-700 italic bg-white p-3 rounded-lg border border-indigo-100">"{aiInsights[fund.code]}"</p>
                      )}
                    </div>
                  ))}
                </div>
              </motion.div>
            ))}
          </div>
        )}
      </section>

      <section>
        <div className="flex items-center gap-2 mb-4">
          <BarChart3 className="text-blue-600 w-5 h-5" />
          <h3 className="text-xl font-bold text-slate-900">Stock Strategies</h3>
        </div>
        {groupedLoading ? <SkeletonGrid count={3} /> : (
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {Object.entries(groupedStocks).map(([strategy, stocks]) => (
              <motion.div key={strategy} whileHover={{ y: -4 }} className="bg-white p-5 rounded-2xl border border-slate-200 shadow-sm">
                <h4 className="font-bold text-lg text-blue-700 mb-4">{strategy}</h4>
                <div className="space-y-3">
                  {filterStocks(stocks).map((stock, idx) => (
                    <div key={idx} className="flex justify-between items-center p-3 bg-slate-50 rounded-xl">
                      <div>
                        <p className="font-bold text-slate-900">{stock.symbol}</p>
                        <p className="text-xs text-slate-500">{stock.sector} • Score: {stock.score}</p>
                      </div>
                      <div className="text-right">
                        <p className="font-semibold">₹{stock.price != null ? Number(stock.price).toLocaleString('en-IN') : '—'}</p>
                        <p className="text-xs text-slate-500">P/E: {stock.pe ?? '—'}</p>
                      </div>
                    </div>
                  ))}
                </div>
              </motion.div>
            ))}
          </div>
        )}
      </section>
    </div>
  );
}

function LiveMarketTab() {
  const [rows, setRows] = useState([]);
  const [query, setQuery] = useState('');
  const [appliedQuery, setAppliedQuery] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [pagination, setPagination] = useState({ total: 0, has_more: false });
  const [livePrices, setLivePrices] = useState({});

  const loadPage = async (offset = 0, q = appliedQuery) => {
    setLoading(true);
    setError('');
    try {
      const params = new URLSearchParams({ limit: '80', offset: String(offset) });
      if (q.trim()) params.set('q', q.trim());
      const res = await fetch(`${API}/api/live/market?${params}`);
      const body = await res.json();
      if (!res.ok || !body.success) throw new Error(body.detail || 'Failed to load live market');
      if (offset === 0) {
        setRows(body.data || []);
        setLivePrices({});
      } else {
        setRows((prev) => [...prev, ...(body.data || [])]);
      }
      setPagination(body.pagination || { total: 0, has_more: false });
    } catch (err) {
      setError(err.message || 'Failed to load live market');
      if (offset === 0) setRows([]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { loadPage(0, ''); }, []);

  useEffect(() => {
    if (!rows.length) return;
    let stopped = false;
    let cursor = 0;
    const tick = async () => {
      const symbols = rows.map((row) => row.symbol).filter(Boolean);
      if (!symbols.length) return;
      const chunk = symbols.slice(cursor, cursor + 25);
      cursor = (cursor + 25) % symbols.length;
      try {
        const res = await fetch(`${API}/api/live/quotes?symbols=${encodeURIComponent(chunk.join(','))}`);
        const body = await res.json();
        if (!stopped && body.data) setLivePrices((prev) => ({ ...prev, ...body.data }));
      } catch {
        /* keep cached prices */
      }
    };
    tick();
    const id = setInterval(tick, 3000);
    return () => { stopped = true; clearInterval(id); };
  }, [rows]);

  return (
    <div>
      <div className="flex items-center gap-3 mb-6">
        <div className="relative">
          <Activity className="text-red-500 w-6 h-6" />
          <span className="absolute top-0 right-0 w-2 h-2 bg-red-500 rounded-full animate-ping" />
        </div>
        <div>
          <h2 className="text-2xl font-bold text-slate-900">Live Market</h2>
          <p className="text-sm text-slate-500">NSE quotes across the listed universe</p>
        </div>
      </div>
      <div className="bg-white p-4 rounded-2xl border border-slate-200 shadow-sm mb-6">
        <div className="flex flex-col md:flex-row gap-3">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400 w-4 h-4" />
            <input
              type="search"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onKeyDown={(e) => { if (e.key === 'Enter') { setAppliedQuery(query); loadPage(0, query); } }}
              placeholder="Search symbol or company"
              className="w-full pl-10 pr-3 py-2.5 bg-slate-50 border border-slate-200 rounded-xl focus:ring-2 focus:ring-indigo-500 outline-none"
            />
          </div>
          <button type="button" onClick={() => { setAppliedQuery(query); loadPage(0, query); }} className="px-5 py-2.5 bg-indigo-600 text-white rounded-xl font-semibold hover:bg-indigo-700">
            Search
          </button>
        </div>
        <p className="text-sm text-slate-500 mt-3">Showing {rows.length.toLocaleString('en-IN')} of {(pagination.total || 0).toLocaleString('en-IN')} listed stocks</p>
      </div>
      {error && <p className="text-sm text-red-600 mb-4">{error}</p>}
      {loading && rows.length === 0 ? <p className="text-center text-slate-500 py-12">Loading NSE stocks...</p> : rows.length === 0 ? (
        <EmptyState text="No stocks match that search." />
      ) : (
        <>
          <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-5 gap-4">
            {rows.map((row) => {
              const live = livePrices[row.symbol];
              const price = live ?? row.price;
              return (
                <div key={row.symbol} className="bg-white p-4 rounded-2xl border border-slate-200 shadow-sm">
                  <div className="flex items-start justify-between gap-2">
                    <p className="font-bold text-slate-900">{row.symbol}</p>
                    {live != null && <span className="w-2 h-2 mt-1 rounded-full bg-red-500 animate-pulse" />}
                  </div>
                  <p className="text-xs text-slate-500 truncate mt-0.5" title={row.name}>{row.name}</p>
                  <p className="text-xl font-bold text-slate-900 mt-3">
                    {price != null ? `₹${Number(price).toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}` : '—'}
                  </p>
                </div>
              );
            })}
          </div>
          {pagination.has_more && (
            <LoadMore onClick={() => loadPage(rows.length, appliedQuery)} loading={loading} remaining={pagination.total - rows.length} />
          )}
        </>
      )}
    </div>
  );
}

function BacktestTab({ backtestSymbols, setBacktestSymbols, runBacktest, isBacktesting, backtestResults }) {
  return (
    <div className="max-w-4xl mx-auto">
      <SectionTitle icon={RefreshCw} color="text-indigo-600" title="Strategy Backtester" subtitle="50/200 SMA crossover over 3 years" />
      <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm mb-8">
        <label className="block text-sm font-semibold text-slate-700 mb-2">Enter stock symbols (comma-separated)</label>
        <div className="flex flex-col sm:flex-row gap-4">
          <input
            type="text"
            value={backtestSymbols}
            onChange={(e) => setBacktestSymbols(e.target.value)}
            className="flex-1 px-4 py-3 bg-slate-50 border border-slate-200 rounded-xl focus:ring-2 focus:ring-indigo-500 outline-none"
            placeholder="RELIANCE,TCS,HDFCBANK"
          />
          <button onClick={runBacktest} disabled={isBacktesting} className="px-6 py-3 bg-indigo-600 text-white rounded-xl hover:bg-indigo-700 disabled:opacity-50 font-semibold flex items-center justify-center gap-2">
            <RefreshCw className={cn('w-4 h-4', isBacktesting && 'animate-spin')} />
            {isBacktesting ? 'Running...' : 'Run Backtest'}
          </button>
        </div>
        <p className="text-xs text-slate-500 mt-3 flex items-center gap-1"><Filter className="w-3 h-3" /> Default strategy: 50/200 SMA crossover over 3 years.</p>
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

function MFDashboard({ report }) {
  const summary = report.summary || {};
  const holdings = report.holdings || [];
  const actions = report.verdict?.actions || [];
  const isPositive = (summary.gain || 0) >= 0;
  return (
    <div className="space-y-6">
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <SummaryCard title="Invested" value={summary.invested} subtitle={`${summary.funds || holdings.length} schemes`} />
        <SummaryCard title="Current Value" value={summary.value} subtitle={`XIRR: ${summary.xirr ?? 'N/A'}%`} />
        <div className={cn('p-6 rounded-2xl border shadow-sm', isPositive ? 'bg-emerald-50 border-emerald-100' : 'bg-red-50 border-red-100')}>
          <p className="text-sm font-medium text-slate-600 mb-2">Total Returns</p>
          <p className={cn('text-3xl font-bold', isPositive ? 'text-emerald-700' : 'text-red-700')}>₹{(summary.gain || 0).toLocaleString('en-IN')}</p>
          <p className="text-sm font-semibold mt-1">{isPositive ? '+' : ''}{summary.ret_pct}%</p>
        </div>
      </div>
      {actions.length > 0 && (
        <div className="bg-white p-6 rounded-2xl border border-slate-200 space-y-3">
          <h3 className="font-semibold text-slate-900">Insights</h3>
          {actions.slice(0, 4).map((a, i) => <p key={i} className="text-sm text-amber-800 bg-amber-50 border border-amber-100 rounded-xl p-3">{a}</p>)}
        </div>
      )}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {holdings.slice(0, 8).map((h, i) => (
          <div key={i} className="p-4 rounded-2xl border border-slate-200 bg-white">
            <p className="font-semibold text-sm text-slate-900">{h.name}</p>
            <div className="flex justify-between mt-2 text-sm">
              <span className="text-slate-500">₹{(h.invested || 0).toLocaleString('en-IN')}</span>
              <span className="font-medium">₹{(h.value || 0).toLocaleString('en-IN')}</span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

function StockDashboard({ report }) {
  const summary = report.summary || {};
  const holdings = report.holdings || [];
  const alerts = report.recommendations?.alerts || [];
  const isPositive = (summary.total_gain || 0) >= 0;
  return (
    <div className="space-y-6">
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <SummaryCard title="Invested" value={summary.total_invested} subtitle={`${summary.total_stocks || holdings.length} stocks`} />
        <SummaryCard title="Current Value" value={summary.total_value} subtitle={`${isPositive ? '+' : ''}${summary.overall_return_pct}%`} />
        <div className={cn('p-6 rounded-2xl border', isPositive ? 'bg-emerald-50 border-emerald-100' : 'bg-red-50 border-red-100')}>
          <p className="text-sm font-medium text-slate-600 mb-2">Total Gain</p>
          <p className={cn('text-3xl font-bold', isPositive ? 'text-emerald-700' : 'text-red-700')}>₹{(summary.total_gain || 0).toLocaleString('en-IN')}</p>
        </div>
      </div>
      {alerts.map((a, i) => <p key={i} className="text-sm text-red-800 bg-red-50 border border-red-100 rounded-xl p-3">{a.message}</p>)}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {holdings.map((h) => (
          <div key={h.symbol} className="p-4 rounded-2xl border border-slate-200 bg-white">
            <div className="flex justify-between">
              <p className="font-semibold text-slate-900">{h.symbol}</p>
              <span className={cn('text-sm font-bold', (h.gain || 0) >= 0 ? 'text-emerald-700' : 'text-red-700')}>{(h.gain || 0) >= 0 ? '+' : ''}{h.return_pct ?? h.ret_pct}%</span>
            </div>
            <div className="flex justify-between mt-2 text-sm text-slate-600">
              <span>₹{(h.invested || 0).toLocaleString('en-IN')}</span>
              <span>₹{(h.current_value || h.value || 0).toLocaleString('en-IN')}</span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

function SortableTh({ label, sortKey, current, dir, onSort }) {
  const active = current === sortKey;
  return (
    <th className="px-6 py-3 text-left">
      <button type="button" onClick={() => onSort(sortKey)} className={cn('inline-flex items-center gap-1 text-xs font-semibold uppercase tracking-wide', active ? 'text-slate-900' : 'text-slate-500 hover:text-slate-800')}>
        {label}
        {active ? (dir === 'asc' ? <ChevronUp size={14} /> : <ChevronDown size={14} />) : <span className="text-[10px] text-slate-300">↕</span>}
      </button>
    </th>
  );
}

function DataTable({ children }) {
  return (
    <div className="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden">
      <table className="w-full text-left">{children}</table>
    </div>
  );
}

function LoadMore({ onClick, loading, remaining }) {
  return (
    <div className="text-center mt-6">
      <button type="button" onClick={onClick} disabled={loading} className="px-4 py-2 text-sm font-medium text-indigo-700 bg-indigo-50 rounded-xl disabled:opacity-50">
        {loading ? 'Loading...' : `Load more (${Number(remaining || 0).toLocaleString('en-IN')} remaining)`}
      </button>
    </div>
  );
}

function EmptyState({ text }) {
  return <p className="text-center text-slate-500 py-12 bg-white rounded-2xl border border-slate-200">{text}</p>;
}

function SkeletonGrid({ count }) {
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
      {Array.from({ length: count }).map((_, i) => (
        <div key={i} className="bg-white p-5 rounded-2xl border border-slate-200 shadow-sm h-64 animate-pulse">
          <div className="h-6 bg-slate-200 rounded w-1/3 mb-4" />
          <div className="space-y-3">
            <div className="h-16 bg-slate-100 rounded-xl" />
            <div className="h-16 bg-slate-100 rounded-xl" />
          </div>
        </div>
      ))}
    </div>
  );
}

function SkeletonTable() {
  return <div className="bg-white rounded-2xl border border-slate-200 h-64 animate-pulse" />;
}

function fmtNav(value) {
  if (value == null || value === '') return '—';
  const n = Number(value);
  if (Number.isNaN(n)) return '—';
  return n.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 4 });
}

function fmtPct(value) {
  if (value == null || value === '') return '—';
  const n = Number(value);
  if (Number.isNaN(n)) return '—';
  const cls = n >= 0 ? 'text-emerald-700' : 'text-red-700';
  return <span className={`font-medium ${cls}`}>{n >= 0 ? '+' : ''}{n.toFixed(2)}%</span>;
}

function SummaryCard({ title, value, subtitle }) {
  return (
    <div className="bg-white p-6 rounded-2xl shadow-sm border border-slate-200">
      <p className="text-sm font-medium text-slate-500 mb-2">{title}</p>
      <p className="text-2xl font-bold text-slate-900">₹{(value || 0).toLocaleString('en-IN')}</p>
      <p className="text-xs text-slate-400 mt-1">{subtitle}</p>
    </div>
  );
}

export default App;
