import { Wallet } from 'lucide-react';
import { cn, SectionTitle, SummaryCard, DataTable, EmptyState } from './ui';
import PortfolioInsights from './PortfolioInsights';

function inr(n, digits = 0) {
  if (n == null || n === '') return '—';
  return `₹${Number(n).toLocaleString('en-IN', { minimumFractionDigits: digits, maximumFractionDigits: digits })}`;
}

function pct(n) {
  if (n == null || n === '') return '—';
  const v = Number(n);
  return `${v > 0 ? '+' : ''}${v.toFixed(2)}%`;
}

function when(iso) {
  if (!iso) return null;
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleString('en-IN', { dateStyle: 'medium', timeStyle: 'short' });
}

export default function MyPortfolioTab({ snapshot, recommendations, onUpload }) {
  const funds = snapshot?.mutual_funds || [];
  const stocks = snapshot?.stocks || [];
  const summary = snapshot?.summary || {};
  const hasBook = funds.length > 0 || stocks.length > 0;

  const invested = (summary.stocks?.invested || 0) + (summary.mutual_funds?.invested || 0);
  const current = (summary.stocks?.current || 0) + (summary.mutual_funds?.current || 0);
  const gain = current - invested;
  const ret = invested > 0 ? (gain / invested) * 100 : null;
  const isPos = gain >= 0;

  const updated = [snapshot?.mf_updated_at, snapshot?.stock_updated_at].filter(Boolean).sort().slice(-1)[0];

  if (!hasBook) {
    return (
      <div>
        <SectionTitle icon={Wallet} color="text-indigo-600" title="My Portfolio" subtitle="Saved holdings stay here until you upload a new CAS or stock file" />
        <EmptyState text="No saved portfolio yet. Upload a CAS or stock file to build this book." />
        {onUpload && (
          <div className="text-center mt-4">
            <button type="button" onClick={onUpload} className="px-5 py-2.5 bg-indigo-600 text-white text-sm font-semibold rounded-xl">
              Go to Upload
            </button>
          </div>
        )}
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <SectionTitle
        icon={Wallet}
        color="text-indigo-600"
        title="My Portfolio"
        subtitle={updated ? `Last saved ${when(updated)}. Unchanged until you upload another file.` : 'Saved locally. Unchanged until you upload another file.'}
      />

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3 md:gap-4">
        <SummaryCard title="Invested" value={invested} subtitle={`${funds.length} funds · ${stocks.length} stocks`} />
        <SummaryCard title="Current value" value={current} />
        <div className={cn('p-4 md:p-6 rounded-2xl border shadow-sm', isPos ? 'bg-emerald-50 border-emerald-100' : 'bg-red-50 border-red-100')}>
          <p className="text-xs md:text-sm font-medium text-slate-600 mb-1">Total returns</p>
          {invested > 0 ? (
            <>
              <p className={cn('text-xl md:text-2xl font-bold', isPos ? 'text-emerald-700' : 'text-red-700')}>
                {isPos ? '+' : ''}{inr(gain)}
              </p>
              <p className="text-xs font-semibold mt-1">{pct(ret)}</p>
            </>
          ) : (
            <p className="text-xl font-bold text-slate-400">—</p>
          )}
        </div>
        <div className="bg-white p-4 md:p-6 rounded-2xl border border-slate-200 shadow-sm">
          <p className="text-xs md:text-sm font-medium text-slate-500 mb-2">Mix</p>
          <p className="text-sm text-slate-800">Funds {inr(summary.mutual_funds?.current)}</p>
          <p className="text-sm text-slate-800 mt-1">Stocks {inr(summary.stocks?.current)}</p>
        </div>
      </div>

      {(snapshot?.mf_file || snapshot?.stock_file) && (
        <p className="text-xs text-slate-500">
          {snapshot.mf_file ? `Funds from ${snapshot.mf_file}. ` : ''}
          {snapshot.stock_file ? `Stocks from ${snapshot.stock_file}.` : ''}
        </p>
      )}

      <PortfolioInsights recommendations={recommendations} summary={summary} />

      {funds.length > 0 && (
        <div>
          <h3 className="text-base font-bold text-slate-900 mb-3">Mutual funds ({funds.length})</h3>
          <DataTable>
            <thead className="bg-slate-50 text-slate-500 text-xs uppercase">
              <tr>
                <th className="px-4 py-3">Scheme</th>
                <th className="px-4 py-3">Category</th>
                <th className="px-4 py-3 text-right">Units</th>
                <th className="px-4 py-3 text-right">Invested</th>
                <th className="px-4 py-3 text-right">Value</th>
                <th className="px-4 py-3 text-right">Return</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {funds.map((f) => {
                const retv = f.return_pct;
                const pos = Number(retv || 0) >= 0;
                return (
                  <tr key={f.scheme_code || f.scheme_name} className="text-sm">
                    <td className="px-4 py-3">
                      <p className="font-medium text-slate-900">{f.scheme_name}</p>
                      <p className="text-[11px] text-slate-500">{f.amc || '—'}</p>
                    </td>
                    <td className="px-4 py-3 text-slate-600">{f.category || f.bucket || '—'}</td>
                    <td className="px-4 py-3 text-right tabular-nums">{f.units != null ? Number(f.units).toLocaleString('en-IN', { maximumFractionDigits: 3 }) : '—'}</td>
                    <td className="px-4 py-3 text-right tabular-nums">{inr(f.invested_value)}</td>
                    <td className="px-4 py-3 text-right tabular-nums font-medium">{inr(f.current_value)}</td>
                    <td className={cn('px-4 py-3 text-right tabular-nums font-semibold', retv == null ? 'text-slate-400' : pos ? 'text-emerald-700' : 'text-red-700')}>
                      {pct(retv)}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </DataTable>
        </div>
      )}

      {stocks.length > 0 && (
        <div>
          <h3 className="text-base font-bold text-slate-900 mb-3">Stocks ({stocks.length})</h3>
          <DataTable>
            <thead className="bg-slate-50 text-slate-500 text-xs uppercase">
              <tr>
                <th className="px-4 py-3">Symbol</th>
                <th className="px-4 py-3">Sector</th>
                <th className="px-4 py-3 text-right">Qty</th>
                <th className="px-4 py-3 text-right">Avg</th>
                <th className="px-4 py-3 text-right">Invested</th>
                <th className="px-4 py-3 text-right">Value</th>
                <th className="px-4 py-3 text-right">Return</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {stocks.map((s) => {
                const retv = s.return_pct;
                const pos = Number(retv || 0) >= 0;
                return (
                  <tr key={s.symbol} className="text-sm">
                    <td className="px-4 py-3">
                      <p className="font-medium text-slate-900">{s.symbol}</p>
                      <p className="text-[11px] text-slate-500">{s.name || '—'}</p>
                    </td>
                    <td className="px-4 py-3 text-slate-600">{s.sector || '—'}</td>
                    <td className="px-4 py-3 text-right tabular-nums">{s.quantity != null ? Number(s.quantity).toLocaleString('en-IN') : '—'}</td>
                    <td className="px-4 py-3 text-right tabular-nums">{inr(s.buy_price, 2)}</td>
                    <td className="px-4 py-3 text-right tabular-nums">{inr(s.invested_value)}</td>
                    <td className="px-4 py-3 text-right tabular-nums font-medium">{inr(s.current_value)}</td>
                    <td className={cn('px-4 py-3 text-right tabular-nums font-semibold', retv == null ? 'text-slate-400' : pos ? 'text-emerald-700' : 'text-red-700')}>
                      {pct(retv)}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </DataTable>
        </div>
      )}
    </div>
  );
}
