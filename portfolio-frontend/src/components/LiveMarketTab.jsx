import { useState, useEffect, useRef } from 'react';
import { Activity, Search } from 'lucide-react';
import { cn, LoadMore, EmptyState } from './ui';

import { cn, LoadMore, EmptyState } from './ui';
import { API } from '../api';

export default function LiveMarketTab({ active = true }) {
  const [rows, setRows] = useState([]);
  const [query, setQuery] = useState('');
  const [appliedQuery, setAppliedQuery] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [pagination, setPagination] = useState({ total: 0, has_more: false });
  const [livePrices, setLivePrices] = useState({});
  const [prevPrices, setPrevPrices] = useState({});
  const [updatedAt, setUpdatedAt] = useState(null);
  const [now, setNow] = useState(Date.now());
  const [refreshing, setRefreshing] = useState(false);
  const livePricesRef = useRef({});

  const loadPage = async (offset = 0, q = '') => {
    setLoading(true);
    setError('');
    try {
      const params = new URLSearchParams({ limit: '40', offset: String(offset) });
      if (q.trim()) params.set('q', q.trim());
      const res = await fetch(`${API}/api/live/market?${params}`);
      const body = await res.json();
      if (!res.ok || !body.success) throw new Error(body.detail || 'Failed');
      if (offset === 0) {
        setRows(body.data || []);
      } else {
        setRows((prev) => [...prev, ...(body.data || [])]);
      }
      setPagination(body.pagination || { total: 0, has_more: false });
    } catch (err) {
      setError(err.message);
      if (offset === 0) setRows([]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadPage(0, '');
  }, []);

  useEffect(() => {
    livePricesRef.current = livePrices;
  }, [livePrices]);

  useEffect(() => {
    if (!updatedAt) return;
    const id = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(id);
  }, [updatedAt]);

  const symbolKey = rows.map((r) => r.symbol).join(',');

  useEffect(() => {
    if (!active || !symbolKey) return;
    let cancelled = false;
    let timer;

    const poll = async () => {
      const symbols = symbolKey.split(',').filter(Boolean);
      if (!symbols.length || cancelled) return;
      setRefreshing(true);
      const quotes = {};
      try {
        for (let i = 0; i < symbols.length; i += 20) {
          if (cancelled) return;
          const chunk = symbols.slice(i, i + 20);
          const res = await fetch(`${API}/api/live/quotes?symbols=${encodeURIComponent(chunk.join(','))}`, {
            cache: 'no-store',
          });
          const body = await res.json();
          Object.assign(quotes, body.data || {});
        }
        if (cancelled) return;
        setPrevPrices(livePricesRef.current);
        setLivePrices((prev) => ({ ...prev, ...quotes }));
        setUpdatedAt(Date.now());
        setNow(Date.now());
      } catch {
        /* keep last prices */
      } finally {
        if (!cancelled) {
          setRefreshing(false);
          timer = setTimeout(poll, 4000);
        }
      }
    };

    poll();
    return () => {
      cancelled = true;
      clearTimeout(timer);
    };
  }, [symbolKey, active]);

  const ago = updatedAt ? Math.max(0, Math.round((now - updatedAt) / 1000)) : null;

  return (
    <div>
      <div className="flex items-center justify-between gap-3 mb-4 md:mb-6 flex-wrap">
        <div className="flex items-center gap-3">
          <div className="relative">
            <Activity className="text-red-500 w-5 h-5 md:w-6 md:h-6" />
            <span className="absolute top-0 right-0 w-2 h-2 bg-red-500 rounded-full animate-ping" />
          </div>
          <div>
            <h2 className="text-xl md:text-2xl font-bold text-slate-900">Live Market</h2>
            <p className="text-xs md:text-sm text-slate-500">
              {refreshing ? 'Refreshing quotes…' : updatedAt ? `Last quote update ${ago}s ago` : 'Fetching live NSE quotes…'}
            </p>
          </div>
        </div>
      </div>

      <div className="flex gap-3 mb-4">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400 w-4 h-4" />
          <input
            type="search"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={(e) => { if (e.key === 'Enter') { setAppliedQuery(query); loadPage(0, query); } }}
            placeholder="Search RELIANCE, TCS…"
            className="w-full pl-10 pr-3 py-2.5 bg-white border border-slate-200 rounded-xl focus:ring-2 focus:ring-indigo-500 outline-none text-sm"
          />
        </div>
        <button
          onClick={() => { setAppliedQuery(query); loadPage(0, query); }}
          className="px-4 py-2.5 bg-indigo-600 text-white rounded-xl text-sm font-semibold"
        >
          Search
        </button>
      </div>

      {error && <p className="text-sm text-red-600 mb-4">{error}</p>}
      {loading && rows.length === 0 ? (
        <p className="text-center text-slate-500 py-12">Loading...</p>
      ) : rows.length === 0 ? (
        <EmptyState text="No stocks found." />
      ) : (
        <>
          <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-3 md:gap-4">
            {rows.map((row) => {
              const live = livePrices[row.symbol];
              const price = live ?? row.price;
              const prev = prevPrices[row.symbol];
              const delta = live != null && prev != null ? live - prev : 0;
              return (
                <div key={row.symbol} className="bg-white p-3 md:p-4 rounded-2xl border border-slate-200 shadow-sm">
                  <div className="flex items-start justify-between">
                    <p className="font-bold text-slate-900 text-xs md:text-sm">{row.symbol}</p>
                    {live != null && <span className="w-2 h-2 rounded-full bg-red-500 animate-pulse" />}
                  </div>
                  <p className="text-[10px] text-slate-500 truncate mt-0.5">{row.name}</p>
                  <p className={cn(
                    'text-base md:text-xl font-bold mt-2 tabular-nums',
                    delta > 0 ? 'text-emerald-600' : delta < 0 ? 'text-red-600' : 'text-slate-900'
                  )}>
                    {price != null ? `₹${Number(price).toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}` : '—'}
                  </p>
                </div>
              );
            })}
          </div>
          {pagination.has_more && (
            <LoadMore
              onClick={() => loadPage(rows.length, appliedQuery)}
              loading={loading}
              remaining={pagination.total - rows.length}
            />
          )}
        </>
      )}
    </div>
  );
}
