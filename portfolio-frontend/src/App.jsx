import { useState, useEffect } from 'react';
import {
  TrendingUp, Brain, Activity, BarChart3, RefreshCw,
  PieChart, Upload, Wallet
} from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import PortfolioTab from './components/PortfolioTab';
import MyPortfolioTab from './components/MyPortfolioTab';
import AllStocksTab from './components/AllStocksTab';
import AllFundsTab from './components/AllFundsTab';
import GroupedPicksTab from './components/GroupedPicksTab';
import LiveMarketTab from './components/LiveMarketTab';
import BacktestTab from './components/BacktestTab';
import { API } from './api';

const TABS = [
  { id: 'portfolio', label: 'My Portfolio', icon: Wallet },
  { id: 'upload', label: 'Upload', icon: Upload },
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
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [error, setError] = useState('');
  const [casPassword, setCasPassword] = useState('');
  const [stockPassword, setStockPassword] = useState('');

  const [snapshot, setSnapshot] = useState(null);
  const [personalizedRecs, setPersonalizedRecs] = useState(null);

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
    loadSavedPortfolio();
  }, []);

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

  const loadSavedPortfolio = async () => {
    try {
      const [snapRes, recRes] = await Promise.all([
        fetch(`${API}/api/portfolio/snapshot`).then((r) => r.json()).catch(() => ({})),
        fetch(`${API}/api/portfolio/recommendations`).then((r) => r.json()).catch(() => ({})),
      ]);
      if (snapRes.success) setSnapshot(snapRes.data);
      if (recRes.success) setPersonalizedRecs(recRes.data);
    } catch (err) {
      console.error('Failed to load saved portfolio:', err);
    }
  };

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
    formData.append('password', casPassword || '');
    try {
      const response = await fetch(`${API}/api/analyze-cas`, { method: 'POST', body: formData });
      if (!response.ok) {
        const errData = await response.json();
        throw new Error(errData.detail || 'Failed to analyze PDF');
      }
      const result = await response.json();
      if (result.data?.holdings) {
        await fetch(`${API}/api/portfolio/save-mfs`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(result.data.holdings),
        });
        await fetch(`${API}/api/portfolio/save-report`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ kind: 'mf', report: result.data }),
        });
        await loadSavedPortfolio();
        setActiveTab('portfolio');
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setIsAnalyzing(false);
      event.target.value = '';
    }
  };

  const handleStockUpload = async (event) => {
    const file = event.target.files[0];
    if (!file) return;
    setIsAnalyzing(true);
    setError('');
    const formData = new FormData();
    formData.append('file', file);
    formData.append('password', stockPassword || '');
    try {
      const response = await fetch(`${API}/api/analyze-stocks`, { method: 'POST', body: formData });
      if (!response.ok) {
        const errData = await response.json();
        throw new Error(errData.detail || 'Failed to analyze stocks');
      }
      const result = await response.json();
      if (result.data?.holdings) {
        await fetch(`${API}/api/portfolio/save-stocks`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(result.data.holdings),
        });
        await fetch(`${API}/api/portfolio/save-report`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ kind: 'stocks', report: result.data }),
        });
        await loadSavedPortfolio();
        setActiveTab('portfolio');
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setIsAnalyzing(false);
      event.target.value = '';
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
              <MyPortfolioTab
                snapshot={snapshot}
                recommendations={personalizedRecs}
                onUpload={() => setActiveTab('upload')}
              />
            </TabPanel>
          )}

          {activeTab === 'upload' && (
            <TabPanel k="upload">
              <PortfolioTab
                handleMFUpload={handleMFUpload}
                handleStockUpload={handleStockUpload}
                isAnalyzing={isAnalyzing}
                error={error}
                casPassword={casPassword}
                setCasPassword={setCasPassword}
                stockPassword={stockPassword}
                setStockPassword={setStockPassword}
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

export default App;
