import { useState, useEffect } from 'react';
import { TrendingUp, Brain, Activity, BarChart3, Upload, PieChart, RefreshCw } from 'lucide-react';
import { cn } from './components/ui';
import PortfolioTab from './components/PortfolioTab';
import AllStocksTab from './components/AllStocksTab';
import AllFundsTab from './components/AllFundsTab';
import GroupedPicksTab from './components/GroupedPicksTab';
import LiveMarketTab from './components/LiveMarketTab';
import BacktestTab from './components/BacktestTab';
import StockDetailModal from './components/StockDetailModal';
import FundDetailModal from './components/FundDetailModal';
import FundCompare from './components/FundCompare';

const API = 'http://localhost:8000';

const TABS = [
  { id: 'portfolio', label: 'Portfolio', icon: Upload },
  { id: 'stocks', label: 'Stocks', icon: BarChart3 },
  { id: 'funds', label: 'Funds', icon: PieChart },
  { id: 'picks', label: 'Picks', icon: TrendingUp },
  { id: 'live', label: 'Live', icon: Activity },
];

function App() {
  const [activeTab, setActiveTab] = useState('portfolio');
  const [portfolioSubTab, setPortfolioSubTab] = useState('upload');
  const [mfReport, setMfReport] = useState(null);
  const [stockReport, setStockReport] = useState(null);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [error, setError] = useState('');

  const [selectedStock, setSelectedStock] = useState(null);
  const [selectedFund, setSelectedFund] = useState(null);

  const [compareMode, setCompareMode] = useState(false);
  const [selectedForCompare, setSelectedForCompare] = useState([]);
  const [comparisonData, setComparisonData] = useState(null);

  const [allStocks, setAllStocks] = useState([]);
  const [stocksLoading, setStocksLoading] = useState(false);
  const [stocksPagination, setStocksPagination] = useState({ total: 0, has_more: false });
  const [stocksSortBy, setStocksSortBy] = useState('score');
  const [stocksSortDir, setStocksSortDir] = useState('desc');
  const [stocksSector, setStocksSector] = useState('');
  const [stocksSectors, setStocksSectors] = useState([]);
  const [stocksError, setStocksError] = useState('');
  const [stocksQuery, setStocksQuery] = useState('');

  const [allFunds, setAllFunds] = useState([]);
  const [fundsLoading, setFundsLoading] = useState(false);
  const [fundsPagination, setFundsPagination] = useState({ total: 0, has_more: false });
  const [fundsSortBy, setFundsSortBy] = useState('ai_score');
  const [fundsSortDir, setFundsSortDir] = useState('desc');
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
  const [showBacktest, setShowBacktest] = useState(false);
  const [liveVisited, setLiveVisited] = useState(false);

  useEffect(() => { if (activeTab === 'live') setLiveVisited(true); }, [activeTab]);
  useEffect(() => { if (activeTab === 'stocks' && allStocks.length === 0) fetchAllStocks(0); }, [activeTab]);
  useEffect(() => { if (activeTab !== 'funds') return; if (allFunds.length === 0) fetchAllFunds(0); fetchMfCategories(); }, [activeTab]);
  useEffect(() => {
    if (activeTab !== 'picks') return;
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
    setStocksLoading(true); setStocksError('');
    try {
      let url = `${API}/api/stocks/all?limit=50&offset=${offset}&sort_by=${sortBy}&sort_dir=${sortDir}`;
      if (stocksSector) url += `&sector=${encodeURIComponent(stocksSector)}`;
      if (stocksQuery.trim()) url += `&q=${encodeURIComponent(stocksQuery.trim())}`;
      const response = await fetch(url);
      const result = await response.json();
      if (!response.ok || !result.success) throw new Error(result.detail || 'Failed');
      setAllStocks(offset === 0 ? (result.data || []) : (prev) => [...prev, ...(result.data || [])]);
      setStocksPagination(result.pagination || { total: 0, has_more: false });
      if (Array.isArray(result.sectors) && result.sectors.length) setStocksSectors(result.sectors);
    } catch (err) { setStocksError(err.message); if (offset === 0) setAllStocks([]); }
    finally { setStocksLoading(false); }
  };

  const fetchAllFunds = async (offset = 0, overrides = {}) => {
    const sortBy = overrides.sortBy ?? fundsSortBy;
    const sortDir = overrides.sortDir ?? fundsSortDir;
    setFundsLoading(true); setFundsError('');
    try {
      let url = `${API}/api/mutual-funds/all?limit=50&offset=${offset}&sort_by=${sortBy}&sort_dir=${sortDir}`;
      if (fundsCategory) url += `&category=${encodeURIComponent(fundsCategory)}`;
      if (fundsBucket) url += `&bucket=${encodeURIComponent(fundsBucket)}`;
      if (fundsQuery.trim()) url += `&q=${encodeURIComponent(fundsQuery.trim())}`;
      const response = await fetch(url);
      const result = await response.json();
      if (!response.ok || !result.success) throw new Error(result.detail || 'Failed');
      setAllFunds(offset === 0 ? (result.data || []) : (prev) => [...prev, ...(result.data || [])]);
      setFundsPagination(result.pagination || { total: 0, has_more: false });
    } catch (err) { setFundsError(err.message); if (offset === 0) setAllFunds([]); }
    finally { setFundsLoading(false); }
  };

  const fetchMfCategories = async () => {
    try { const r = await fetch(`${API}/api/mutual-funds/categories`); const d = await r.json(); if (d.success) setMfCategories(d.data); } catch {}
  };

  const handleMFUpload = async (event) => {
    const file = event.target.files[0]; if (!file) return;
    setIsAnalyzing(true); setError('');
    const formData = new FormData(); formData.append('file', file); formData.append('password', 'ABCDE1234F');
    try {
      const response = await fetch(`${API}/api/analyze-cas`, { method: 'POST', body: formData });
      if (!response.ok) { const d = await response.json(); throw new Error(d.detail || 'Failed'); }
      const result = await response.json(); setMfReport(result.data); setPortfolioSubTab('mf');
    } catch (err) { setError(err.message); } finally { setIsAnalyzing(false); }
  };

  const handleStockUpload = async (event) => {
    const file = event.target.files[0]; if (!file) return;
    setIsAnalyzing(true); setError('');
    const formData = new FormData(); formData.append('file', file);
    try {
      const response = await fetch(`${API}/api/analyze-stocks`, { method: 'POST', body: formData });
      if (!response.ok) { const d = await response.json(); throw new Error(d.detail || 'Failed'); }
      const result = await response.json(); setStockReport(result.data); setPortfolioSubTab('stocks');
    } catch (err) { setError(err.message); } finally { setIsAnalyzing(false); }
  };

  const fetchAiInsight = async (type, identifier) => {
    if (aiInsights[identifier] && aiInsights[identifier] !== 'loading') return;
    setAiInsights((prev) => ({ ...prev, [identifier]: 'loading' }));
    const endpoint = type === 'stock' ? `${API}/api/ai/stock-insight/${identifier}` : `${API}/api/ai/mf-insight/${identifier}`;
    try { const res = await fetch(endpoint); const data = await res.json(); setAiInsights((prev) => ({ ...prev, [identifier]: data.insight || 'No insight.' })); }
    catch { setAiInsights((prev) => ({ ...prev, [identifier]: 'Failed. Is Ollama running?' })); }
  };

  const toggleCompare = (item, type) => {
    const id = type === 'stock' ? item.symbol : item.code;
    const exists = selectedForCompare.find(s => s.id === id);
    if (exists) setSelectedForCompare(selectedForCompare.filter(s => s.id !== id));
    else { if (selectedForCompare.length >= 4) return; setSelectedForCompare([...selectedForCompare, { id, type, data: item }]); }
  };

  const runComparison = async () => {
    const codes = selectedForCompare.filter(s => s.type === 'fund').map(s => s.id);
    if (codes.length < 2) return;
    try {
      const res = await fetch(`${API}/api/mutual-funds/compare`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(codes) });
      const data = await res.json(); setComparisonData(data.data);
    } catch (err) { console.error(err); }
  };

  const runBacktest = async () => {
    setIsBacktesting(true);
    try { const res = await fetch(`${API}/api/backtest?symbols=${encodeURIComponent(backtestSymbols)}&years=3`); const data = await res.json(); setBacktestResults(data.data); }
    finally { setIsBacktesting(false); }
  };

  return (
    <div className="min-h-screen bg-slate-50 text-slate-900 pb-20 md:pb-0">
      {/* Desktop Nav */}
      <nav className="hidden md:block bg-white/80 border-b border-slate-200 sticky top-0 z-40 backdrop-blur-md">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex items-center justify-between h-16">
          <div className="flex items-center gap-2">
            <div className="bg-indigo-600 p-2 rounded-lg"><Brain className="text-white w-5 h-5" /></div>
            <h1 className="text-xl font-bold bg-gradient-to-r from-indigo-600 to-purple-600 bg-clip-text text-transparent">PrasannaTrade AI</h1>
          </div>
          <div className="flex gap-1 bg-slate-100 p-1 rounded-xl">
            {[...TABS, { id: 'backtest', label: 'Backtest', icon: RefreshCw }].map((tab) => (
              <button key={tab.id} onClick={() => setActiveTab(tab.id)}
                className={cn('flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-all', activeTab === tab.id ? 'bg-white text-indigo-600 shadow-sm' : 'text-slate-600 hover:text-slate-900')}>
                <tab.icon className="w-4 h-4" />{tab.label}
              </button>
            ))}
          </div>
        </div>
      </nav>

      {/* Mobile Header */}
      <div className="md:hidden bg-white border-b border-slate-200 sticky top-0 z-40 px-4 py-3">
        <div className="flex items-center gap-2">
          <div className="bg-indigo-600 p-2 rounded-lg"><Brain className="text-white w-5 h-5" /></div>
          <h1 className="text-lg font-bold bg-gradient-to-r from-indigo-600 to-purple-600 bg-clip-text text-transparent">PrasannaTrade AI</h1>
        </div>
      </div>

      <main className="max-w-7xl mx-auto px-3 sm:px-6 lg:px-8 py-4 md:py-8">
        {activeTab === 'portfolio' && <PortfolioTab portfolioSubTab={portfolioSubTab} setPortfolioSubTab={setPortfolioSubTab} mfReport={mfReport} stockReport={stockReport} handleMFUpload={handleMFUpload} handleStockUpload={handleStockUpload} isAnalyzing={isAnalyzing} error={error} />}
        {activeTab === 'stocks' && <AllStocksTab allStocks={allStocks} stocksLoading={stocksLoading} stocksError={stocksError} stocksPagination={stocksPagination} stocksSortBy={stocksSortBy} stocksSortDir={stocksSortDir} onSortStocks={(key) => { const d = { symbol:'asc',name:'asc',price:'desc',pe:'asc',roe:'desc',score:'desc',sector:'asc' }; const nd = stocksSortBy===key?(stocksSortDir==='asc'?'desc':'asc'):(d[key]||'asc'); setStocksSortBy(key); setStocksSortDir(nd); fetchAllStocks(0,{sortBy:key,sortDir:nd}); }} stocksSector={stocksSector} setStocksSector={setStocksSector} stocksSectors={stocksSectors} stocksQuery={stocksQuery} setStocksQuery={setStocksQuery} fetchAllStocks={fetchAllStocks} onStockClick={setSelectedStock} />}
        {activeTab === 'funds' && <AllFundsTab allFunds={allFunds} fundsLoading={fundsLoading} fundsError={fundsError} fundsPagination={fundsPagination} fundsSortBy={fundsSortBy} fundsSortDir={fundsSortDir} onSortFunds={(key) => { const d = {name:'asc',category:'asc',nav:'desc',ret_1y:'desc',ret_3y:'desc',ai_score:'desc'}; const nd = fundsSortBy===key?(fundsSortDir==='asc'?'desc':'asc'):(d[key]||'asc'); setFundsSortBy(key); setFundsSortDir(nd); fetchAllFunds(0,{sortBy:key,sortDir:nd}); }} fundsCategory={fundsCategory} setFundsCategory={setFundsCategory} fundsBucket={fundsBucket} setFundsBucket={setFundsBucket} fundsQuery={fundsQuery} setFundsQuery={setFundsQuery} mfCategories={mfCategories} fetchAllFunds={fetchAllFunds} onFundClick={setSelectedFund} compareMode={compareMode} setCompareMode={setCompareMode} selectedForCompare={selectedForCompare} toggleCompare={toggleCompare} runComparison={runComparison} comparisonData={comparisonData} setComparisonData={setComparisonData} />}
        {activeTab === 'picks' && <GroupedPicksTab groupedMFs={groupedMFs} groupedStocks={groupedStocks} groupedLoading={groupedLoading} picksQuery={picksQuery} setPicksQuery={setPicksQuery} aiInsights={aiInsights} fetchAiInsight={fetchAiInsight} onStockClick={setSelectedStock} onFundClick={setSelectedFund} />}
        {liveVisited && (
          <div className={activeTab === 'live' ? '' : 'hidden'}>
            <LiveMarketTab active={activeTab === 'live'} />
          </div>
        )}
        {activeTab === 'backtest' && <BacktestTab backtestSymbols={backtestSymbols} setBacktestSymbols={setBacktestSymbols} runBacktest={runBacktest} isBacktesting={isBacktesting} backtestResults={backtestResults} />}
      </main>

      {/* Modals */}
      {selectedStock && <StockDetailModal symbol={selectedStock} onClose={() => setSelectedStock(null)} />}
      {selectedFund && <FundDetailModal code={selectedFund} onClose={() => setSelectedFund(null)} />}
      {comparisonData && <FundCompare data={comparisonData} onClose={() => setComparisonData(null)} />}

      {/* Mobile Bottom Nav */}
      <nav className="md:hidden fixed bottom-0 left-0 right-0 bg-white border-t border-slate-200 z-50 safe-area-pb">
        <div className="grid grid-cols-5 gap-1 px-2 py-2">
          {TABS.map((tab) => (
            <button key={tab.id} onClick={() => setActiveTab(tab.id)}
              className={cn('flex flex-col items-center justify-center gap-0.5 py-2 rounded-lg transition-all', activeTab === tab.id ? 'text-indigo-600 bg-indigo-50' : 'text-slate-500')}>
              <tab.icon className="w-5 h-5" />
              <span className="text-[10px] font-medium">{tab.label}</span>
            </button>
          ))}
        </div>
      </nav>
    </div>
  );
}

export default App;