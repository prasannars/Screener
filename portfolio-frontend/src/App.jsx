import { useState, useEffect } from 'react';
import { TrendingUp, Briefcase, Upload, BarChart3, PieChart, ChevronUp, ChevronDown } from 'lucide-react';

function App() {
  const [mainTab, setMainTab] = useState('portfolio'); // 'portfolio', 'stocks', 'funds'
  const [portfolioSubTab, setPortfolioSubTab] = useState('upload'); // 'upload', 'mf', 'stocks'
  
  // Portfolio data
  const [mfReport, setMfReport] = useState(null);
  const [stockReport, setStockReport] = useState(null);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [error, setError] = useState("");

  // All stocks data
  const [allStocks, setAllStocks] = useState([]);
  const [stocksLoading, setStocksLoading] = useState(false);
  const [stocksPagination, setStocksPagination] = useState({ total: 0, has_more: false });
  const [stocksSortBy, setStocksSortBy] = useState('name');
  const [stocksSortDir, setStocksSortDir] = useState('asc');
  const [stocksSector, setStocksSector] = useState('');
  const [stocksSectors, setStocksSectors] = useState([]);
  const [stocksError, setStocksError] = useState('');
  const [stocksQuery, setStocksQuery] = useState('');

  // All mutual funds data
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

  // Fetch catalogs when a tab is first opened (filters apply on the button)
  useEffect(() => {
    if (mainTab === 'stocks') fetchAllStocks(0);
  }, [mainTab]);

  useEffect(() => {
    if (mainTab === 'funds') {
      fetchAllFunds(0);
      fetchMfCategories();
    }
  }, [mainTab]);

  const fetchAllStocks = async (offset = 0, overrides = {}) => {
    const sortBy = overrides.sortBy ?? stocksSortBy;
    const sortDir = overrides.sortDir ?? stocksSortDir;
    setStocksLoading(true);
    setStocksError('');
    try {
      let url = `http://localhost:8000/api/stocks/all?limit=100&offset=${offset}&sort_by=${sortBy}&sort_dir=${sortDir}`;
      if (stocksSector) url += `&sector=${encodeURIComponent(stocksSector)}`;
      if (stocksQuery.trim()) url += `&q=${encodeURIComponent(stocksQuery.trim())}`;

      const response = await fetch(url);
      const result = await response.json();

      if (!response.ok || !result.success) {
        throw new Error(result.detail || 'Failed to fetch stocks');
      }

      if (offset === 0) {
        setAllStocks(result.data || []);
      } else {
        setAllStocks(prev => [...prev, ...(result.data || [])]);
      }
      setStocksPagination(result.pagination || { total: 0, has_more: false });
      if (Array.isArray(result.sectors) && result.sectors.length) {
        setStocksSectors(result.sectors);
      }
    } catch (err) {
      console.error('Failed to fetch stocks:', err);
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
      let url = `http://localhost:8000/api/mutual-funds/all?limit=100&offset=${offset}&sort_by=${sortBy}&sort_dir=${sortDir}`;
      if (fundsCategory) url += `&category=${encodeURIComponent(fundsCategory)}`;
      if (fundsBucket) url += `&bucket=${encodeURIComponent(fundsBucket)}`;
      if (fundsQuery.trim()) url += `&q=${encodeURIComponent(fundsQuery.trim())}`;

      const response = await fetch(url);
      const result = await response.json();

      if (!response.ok || !result.success) {
        throw new Error(result.detail || 'Failed to fetch funds');
      }

      if (offset === 0) {
        setAllFunds(result.data || []);
      } else {
        setAllFunds(prev => [...prev, ...(result.data || [])]);
      }
      setFundsPagination(result.pagination || { total: 0, has_more: false });
    } catch (err) {
      console.error('Failed to fetch funds:', err);
      setFundsError(err.message || 'Failed to fetch funds');
      if (offset === 0) setAllFunds([]);
    } finally {
      setFundsLoading(false);
    }
  };

  const fetchMfCategories = async () => {
    try {
      const response = await fetch('http://localhost:8000/api/mutual-funds/categories');
      const result = await response.json();
      if (result.success) {
        setMfCategories(result.data);
      }
    } catch (err) {
      console.error('Failed to fetch categories:', err);
    }
  };

  // Upload handlers
  const handleMFUpload = async (event) => {
    const file = event.target.files[0];
    if (!file) return;

    setIsAnalyzing(true);
    setError("");

    const formData = new FormData();
    formData.append("file", file);
    formData.append("password", "ABCDE1234F");

    try {
      const response = await fetch("http://localhost:8000/api/analyze-cas", {
        method: "POST",
        body: formData,
      });

      if (!response.ok) {
        const errData = await response.json();
        throw new Error(errData.detail || "Failed to analyze PDF");
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
    setError("");

    const formData = new FormData();
    formData.append("file", file);

    try {
      const response = await fetch("http://localhost:8000/api/analyze-stocks", {
        method: "POST",
        body: formData,
      });

      if (!response.ok) {
        const errData = await response.json();
        throw new Error(errData.detail || "Failed to analyze stocks");
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

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Main Navigation */}
      <nav className="bg-white border-b border-gray-200 sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between h-16">
            <div className="flex items-center">
              <h1 className="text-xl font-bold text-gray-900">PrasannaTrade</h1>
            </div>
            <div className="flex space-x-1">
              <button
                onClick={() => setMainTab('portfolio')}
                className={`px-4 py-2 rounded-lg font-medium transition-colors ${
                  mainTab === 'portfolio' ? 'bg-blue-600 text-white' : 'text-gray-700 hover:bg-gray-100'
                }`}
              >
                <div className="flex items-center gap-2">
                  <PieChart size={18} />
                  My Portfolio
                </div>
              </button>
              <button
                onClick={() => setMainTab('stocks')}
                className={`px-4 py-2 rounded-lg font-medium transition-colors ${
                  mainTab === 'stocks' ? 'bg-green-600 text-white' : 'text-gray-700 hover:bg-gray-100'
                }`}
              >
                <div className="flex items-center gap-2">
                  <BarChart3 size={18} />
                  All Stocks India
                </div>
              </button>
              <button
                onClick={() => setMainTab('funds')}
                className={`px-4 py-2 rounded-lg font-medium transition-colors ${
                  mainTab === 'funds' ? 'bg-purple-600 text-white' : 'text-gray-700 hover:bg-gray-100'
                }`}
              >
                <div className="flex items-center gap-2">
                  <TrendingUp size={18} />
                  All Mutual Funds
                </div>
              </button>
            </div>
          </div>
        </div>
      </nav>

      {/* Main Content */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {mainTab === 'portfolio' && (
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
        )}

        {mainTab === 'stocks' && (
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
        )}

        {mainTab === 'funds' && (
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
        )}
      </div>
    </div>
  );
}

// Portfolio Tab Component
function PortfolioTab({ portfolioSubTab, setPortfolioSubTab, mfReport, stockReport, handleMFUpload, handleStockUpload, isAnalyzing, error }) {
  return (
    <div>
      {/* Portfolio Sub-navigation */}
      <div className="flex gap-2 mb-6">
        <button
          onClick={() => setPortfolioSubTab('upload')}
          className={`px-4 py-2 rounded-lg font-medium transition-colors ${
            portfolioSubTab === 'upload' ? 'bg-gray-900 text-white' : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
          }`}
        >
          <div className="flex items-center gap-2">
            <Upload size={18} />
            Upload
          </div>
        </button>
        {mfReport && (
          <button
            onClick={() => setPortfolioSubTab('mf')}
            className={`px-4 py-2 rounded-lg font-medium transition-colors ${
              portfolioSubTab === 'mf' ? 'bg-blue-600 text-white' : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
            }`}
          >
            Mutual Funds
          </button>
        )}
        {stockReport && (
          <button
            onClick={() => setPortfolioSubTab('stocks')}
            className={`px-4 py-2 rounded-lg font-medium transition-colors ${
              portfolioSubTab === 'stocks' ? 'bg-green-600 text-white' : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
            }`}
          >
            Stocks
          </button>
        )}
      </div>

      {/* Upload Section */}
      {portfolioSubTab === 'upload' && (
        <div className="space-y-6">
          <h2 className="text-2xl font-bold text-gray-900 mb-6">Upload Your Portfolio</h2>
          
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {/* MF Upload */}
            <div className="bg-blue-50 border-2 border-dashed border-blue-200 rounded-2xl p-8 text-center hover:bg-blue-100 transition-colors">
              <div className="flex flex-col items-center gap-4">
                <div className="p-4 bg-blue-100 rounded-full">
                  <TrendingUp size={32} className="text-blue-600" />
                </div>
                <div>
                  <p className="text-lg font-semibold text-gray-900">Mutual Fund CAS PDF</p>
                  <p className="text-sm text-gray-500 mt-1">CAMS, KFintech, NSDL, or CDSL</p>
                </div>
                <label className="cursor-pointer bg-blue-600 hover:bg-blue-700 text-white font-medium py-3 px-8 rounded-xl transition-colors">
                  {isAnalyzing ? "Analyzing..." : "Choose PDF"}
                  <input type="file" accept=".pdf" className="hidden" onChange={handleMFUpload} disabled={isAnalyzing} />
                </label>
              </div>
            </div>

            {/* Stock Upload */}
            <div className="bg-green-50 border-2 border-dashed border-green-200 rounded-2xl p-8 text-center hover:bg-green-100 transition-colors">
              <div className="flex flex-col items-center gap-4">
                <div className="p-4 bg-green-100 rounded-full">
                  <BarChart3 size={32} className="text-green-600" />
                </div>
                <div>
                  <p className="text-lg font-semibold text-gray-900">Stock Portfolio Excel/CSV</p>
                  <p className="text-sm text-gray-500 mt-1">Columns: Symbol, Quantity, Buy Price, Buy Date</p>
                </div>
                <label className="cursor-pointer bg-green-600 hover:bg-green-700 text-white font-medium py-3 px-8 rounded-xl transition-colors">
                  {isAnalyzing ? "Analyzing..." : "Choose Excel/CSV"}
                  <input type="file" accept=".xlsx,.xls,.csv" className="hidden" onChange={handleStockUpload} disabled={isAnalyzing} />
                </label>
              </div>
            </div>
          </div>

          {error && <p className="text-sm text-red-600 mt-4 font-medium text-center">{error}</p>}
        </div>
      )}

      {/* MF Dashboard */}
      {portfolioSubTab === 'mf' && mfReport && <MFDashboard report={mfReport} />}

      {/* Stocks Dashboard */}
      {portfolioSubTab === 'stocks' && stockReport && <StockDashboard report={stockReport} />}
    </div>
  );
}

function AllStocksTab({ allStocks, stocksLoading, stocksError, stocksPagination, stocksSortBy, stocksSortDir, onSortStocks, stocksSector, setStocksSector, stocksSectors, stocksQuery, setStocksQuery, fetchAllStocks }) {
  const fallbackSectors = ['Technology', 'Financial Services', 'Healthcare', 'Energy', 'Consumer Cyclical', 'Industrials', 'Consumer Defensive', 'Basic Materials', 'Utilities', 'Communication Services', 'Real Estate'];
  const sectors = stocksSectors?.length ? stocksSectors : fallbackSectors;

  return (
    <div>
      <h2 className="text-2xl font-bold text-gray-900 mb-6">All Indian Stocks</h2>

      <div className="bg-white p-4 rounded-xl border border-gray-200 mb-6">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="md:col-span-2">
            <label className="block text-sm font-medium text-gray-700 mb-2">Search</label>
            <input
              type="search"
              value={stocksQuery}
              onChange={(e) => setStocksQuery(e.target.value)}
              onKeyDown={(e) => { if (e.key === 'Enter') fetchAllStocks(0); }}
              placeholder="Symbol or company name"
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-green-500"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Sector</label>
            <select
              value={stocksSector}
              onChange={(e) => setStocksSector(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-green-500"
            >
              <option value="">All Sectors</option>
              {sectors.map(sector => (
                <option key={sector} value={sector}>{sector}</option>
              ))}
            </select>
          </div>
          <div className="flex items-end">
            <button
              type="button"
              onClick={() => fetchAllStocks(0)}
              disabled={stocksLoading}
              className="w-full px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors disabled:opacity-60"
            >
              {stocksLoading ? 'Applying...' : 'Apply Filters'}
            </button>
          </div>
        </div>
        <p className="text-xs text-gray-500 mt-3">Click a column header to sort. Click again to reverse.</p>
      </div>

      {stocksPagination?.total > 0 && (
        <p className="text-sm text-gray-600 mb-3">Showing {allStocks.length.toLocaleString('en-IN')} of {stocksPagination.total.toLocaleString('en-IN')} listed stocks</p>
      )}

      {stocksError && (
        <p className="text-sm text-red-600 mb-4 font-medium">{stocksError}</p>
      )}

      {stocksLoading && allStocks.length === 0 ? (
        <div className="text-center py-12">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-green-600 mx-auto"></div>
          <p className="mt-4 text-gray-600">Loading prices, P/E, ROE and scores…</p>
        </div>
      ) : allStocks.length === 0 ? (
        <div className="text-center py-12 bg-white rounded-xl border border-gray-200 text-gray-600">
          No stocks match these filters.
        </div>
      ) : (
        <>
          <div className="relative bg-white rounded-xl border border-gray-200 overflow-hidden">
            {stocksLoading && (
              <div className="absolute inset-0 bg-white/70 flex items-center justify-center z-10">
                <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-green-600"></div>
              </div>
            )}
            <table className="w-full">
              <thead className="bg-gray-50 border-b border-gray-200">
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
              <tbody className="divide-y divide-gray-100">
                {allStocks.map((s) => (
                  <tr key={s.symbol} className="hover:bg-gray-50">
                    <td className="px-6 py-3 text-sm font-semibold text-gray-900">{s.symbol}</td>
                    <td className="px-6 py-3 text-sm text-gray-700">{s.name || '—'}</td>
                    <td className="px-6 py-3 text-sm text-gray-700">{s.current_price != null ? `₹${s.current_price.toLocaleString('en-IN')}` : '—'}</td>
                    <td className="px-6 py-3 text-sm text-gray-700">{s.pe_ratio ?? '—'}</td>
                    <td className="px-6 py-3 text-sm text-gray-700">{s.roe != null ? `${Number(s.roe).toFixed(1)}%` : '—'}</td>
                    <td className="px-6 py-3 text-sm font-medium text-green-700">{s.score ?? '—'} {s.grade ? `(${s.grade})` : ''}</td>
                    <td className="px-6 py-3 text-sm text-gray-500">{s.sector || '—'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {stocksPagination?.has_more && (
            <div className="text-center mt-4">
              <button
                type="button"
                onClick={() => fetchAllStocks(allStocks.length)}
                className="px-4 py-2 text-sm font-medium text-green-700 bg-green-50 rounded-lg hover:bg-green-100"
                disabled={stocksLoading}
              >
                {stocksLoading ? 'Loading...' : `Load more (${stocksPagination.total - allStocks.length} remaining)`}
              </button>
            </div>
          )}
        </>
      )}
    </div>
  );
}

function AllFundsTab({ allFunds, fundsLoading, fundsError, fundsPagination, fundsSortBy, fundsSortDir, onSortFunds, fundsCategory, setFundsCategory, fundsBucket, setFundsBucket, fundsQuery, setFundsQuery, mfCategories, fetchAllFunds }) {
  return (
    <div>
      <h2 className="text-2xl font-bold text-gray-900 mb-6">All Mutual Funds</h2>
      <div className="bg-white p-4 rounded-xl border border-gray-200 mb-6">
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          <div className="lg:col-span-2">
            <label className="block text-sm font-medium text-gray-700 mb-2">Search</label>
            <input
              type="search"
              value={fundsQuery}
              onChange={(e) => setFundsQuery(e.target.value)}
              onKeyDown={(e) => { if (e.key === 'Enter') fetchAllFunds(0); }}
              placeholder="Fund name, AMC, or code"
              className="w-full px-3 py-2 border border-gray-300 rounded-lg"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Category</label>
            <select value={fundsCategory} onChange={(e) => setFundsCategory(e.target.value)} className="w-full px-3 py-2 border border-gray-300 rounded-lg">
              <option value="">All categories</option>
              {(mfCategories.categories || []).map((c) => <option key={c} value={c}>{c}</option>)}
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Bucket</label>
            <select value={fundsBucket} onChange={(e) => setFundsBucket(e.target.value)} className="w-full px-3 py-2 border border-gray-300 rounded-lg">
              <option value="">All buckets</option>
              {(mfCategories.buckets || []).map((b) => <option key={b} value={b}>{b}</option>)}
            </select>
          </div>
        </div>
        <button
          type="button"
          onClick={() => fetchAllFunds(0)}
          disabled={fundsLoading}
          className="mt-4 px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 disabled:opacity-60"
        >
          {fundsLoading ? 'Applying...' : 'Apply Filters'}
        </button>
      </div>
      {fundsError && <p className="text-sm text-red-600 mb-4 font-medium">{fundsError}</p>}
      {fundsPagination?.total > 0 && (
        <p className="text-sm text-gray-600 mb-3">Showing {allFunds.length.toLocaleString('en-IN')} of {fundsPagination.total.toLocaleString('en-IN')} schemes</p>
      )}
      {fundsLoading && allFunds.length === 0 ? (
        <div className="text-center py-12 text-gray-600">Loading NAVs and 1Y/3Y returns…</div>
      ) : allFunds.length === 0 ? (
        <div className="text-center py-12 bg-white rounded-xl border border-gray-200 text-gray-600">No funds match these filters.</div>
      ) : (
        <>
          <div className="relative bg-white rounded-xl border border-gray-200 overflow-hidden">
            {fundsLoading && (
              <div className="absolute inset-0 bg-white/70 flex items-center justify-center z-10">
                <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-purple-600"></div>
              </div>
            )}
            <table className="w-full">
              <thead className="bg-gray-50 border-b border-gray-200">
                <tr>
                  <SortableTh label="Fund" sortKey="name" current={fundsSortBy} dir={fundsSortDir} onSort={onSortFunds} />
                  <SortableTh label="Category" sortKey="category" current={fundsSortBy} dir={fundsSortDir} onSort={onSortFunds} />
                  <SortableTh label="NAV" sortKey="nav" current={fundsSortBy} dir={fundsSortDir} onSort={onSortFunds} />
                  <SortableTh label="1Y" sortKey="ret_1y" current={fundsSortBy} dir={fundsSortDir} onSort={onSortFunds} />
                  <SortableTh label="3Y" sortKey="ret_3y" current={fundsSortBy} dir={fundsSortDir} onSort={onSortFunds} />
                  <SortableTh label="AI Score" sortKey="ai_score" current={fundsSortBy} dir={fundsSortDir} onSort={onSortFunds} />
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {allFunds.map((f) => (
                  <tr key={f.code || f.name} className="hover:bg-gray-50">
                    <td className="px-6 py-3 text-sm font-medium text-gray-900">{f.name}</td>
                    <td className="px-6 py-3 text-sm text-gray-500">{f.category || f.bucket || '—'}</td>
                    <td className="px-6 py-3 text-sm text-gray-700">{fmtNav(f.nav)}</td>
                    <td className="px-6 py-3 text-sm">{fmtPct(f.ret_1y)}</td>
                    <td className="px-6 py-3 text-sm">{fmtPct(f.ret_3y)}</td>
                    <td className="px-6 py-3 text-sm font-medium text-purple-700">{f.ai_score ?? '—'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {fundsPagination?.has_more && (
            <div className="text-center mt-4">
              <button type="button" onClick={() => fetchAllFunds(allFunds.length)} className="px-4 py-2 text-sm font-medium text-purple-700 bg-purple-50 rounded-lg" disabled={fundsLoading}>
                {fundsLoading ? 'Loading...' : `Load more (${(fundsPagination.total - allFunds.length).toLocaleString('en-IN')} remaining)`}
              </button>
            </div>
          )}
        </>
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
        <div className={`p-6 rounded-2xl shadow-sm border ${isPositive ? 'bg-green-50 border-green-100' : 'bg-red-50 border-red-100'}`}>
          <p className="text-sm font-medium text-gray-600 mb-2">Total Returns</p>
          <p className={`text-3xl font-bold ${isPositive ? 'text-green-700' : 'text-red-700'}`}>₹{(summary.gain || 0).toLocaleString('en-IN')}</p>
          <p className="text-sm font-semibold mt-1">{isPositive ? '+' : ''}{summary.ret_pct}%</p>
        </div>
      </div>
      {actions.length > 0 && (
        <div className="bg-white p-6 rounded-2xl border border-gray-100 space-y-3">
          <h3 className="font-semibold text-gray-900">Insights</h3>
          {actions.slice(0, 4).map((a, i) => <p key={i} className="text-sm text-yellow-800 bg-yellow-50 border border-yellow-100 rounded-xl p-3">{a}</p>)}
        </div>
      )}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {holdings.slice(0, 8).map((h, i) => (
          <div key={i} className="p-4 rounded-xl border border-gray-100 bg-white">
            <p className="font-semibold text-sm text-gray-900">{h.name}</p>
            <div className="flex justify-between mt-2 text-sm">
              <span className="text-gray-500">₹{(h.invested || 0).toLocaleString('en-IN')}</span>
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
        <div className={`p-6 rounded-2xl border ${isPositive ? 'bg-green-50 border-green-100' : 'bg-red-50 border-red-100'}`}>
          <p className="text-sm font-medium text-gray-600 mb-2">Total Gain</p>
          <p className={`text-3xl font-bold ${isPositive ? 'text-green-700' : 'text-red-700'}`}>₹{(summary.total_gain || 0).toLocaleString('en-IN')}</p>
        </div>
      </div>
      {alerts.map((a, i) => <p key={i} className="text-sm text-red-800 bg-red-50 border border-red-100 rounded-xl p-3">{a.message}</p>)}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {holdings.map((h) => (
          <div key={h.symbol} className="p-4 rounded-xl border border-gray-100 bg-white">
            <div className="flex justify-between">
              <p className="font-semibold text-gray-900">{h.symbol}</p>
              <span className={`text-sm font-bold ${(h.gain || 0) >= 0 ? 'text-green-700' : 'text-red-700'}`}>{(h.gain || 0) >= 0 ? '+' : ''}{h.return_pct ?? h.ret_pct}%</span>
            </div>
            <div className="flex justify-between mt-2 text-sm text-gray-600">
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
      <button
        type="button"
        onClick={() => onSort(sortKey)}
        className={`inline-flex items-center gap-1 text-xs font-medium uppercase tracking-wide ${
          active ? 'text-gray-900' : 'text-gray-500 hover:text-gray-800'
        }`}
      >
        {label}
        {active ? (
          dir === 'asc' ? <ChevronUp size={14} /> : <ChevronDown size={14} />
        ) : (
          <span className="text-[10px] text-gray-300">↕</span>
        )}
      </button>
    </th>
  );
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
  const cls = n >= 0 ? 'text-green-700' : 'text-red-700';
  return <span className={`font-medium ${cls}`}>{n >= 0 ? '+' : ''}{n.toFixed(2)}%</span>;
}

function SummaryCard({ title, value, subtitle }) {
  return (
    <div className="bg-white p-6 rounded-2xl shadow-sm border border-gray-100">
      <p className="text-sm font-medium text-gray-500 mb-2">{title}</p>
      <p className="text-2xl font-bold text-gray-900">₹{(value || 0).toLocaleString('en-IN')}</p>
      <p className="text-xs text-gray-400 mt-1">{subtitle}</p>
    </div>
  );
}

export default App;