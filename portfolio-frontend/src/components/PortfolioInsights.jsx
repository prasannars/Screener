import { AlertTriangle, Lightbulb, Search, Sparkles } from 'lucide-react';
import { cn } from './ui';

const STYLES = {
  warning: {
    wrap: 'border-rose-200 bg-rose-50/70',
    iconWrap: 'bg-rose-100 text-rose-700',
    Icon: AlertTriangle,
    label: 'Watch',
  },
  opportunity: {
    wrap: 'border-emerald-200 bg-emerald-50/70',
    iconWrap: 'bg-emerald-100 text-emerald-700',
    Icon: Lightbulb,
    label: 'Do this',
  },
  review: {
    wrap: 'border-amber-200 bg-amber-50/70',
    iconWrap: 'bg-amber-100 text-amber-800',
    Icon: Search,
    label: 'Review',
  },
};

function inr(n) {
  return `₹${Number(n || 0).toLocaleString('en-IN', { maximumFractionDigits: 0 })}`;
}

export default function PortfolioInsights({ recommendations, summary }) {
  const recs = [
    ...(recommendations?.overall?.recommendations || []).map((r) => ({ ...r, source: 'Portfolio' })),
    ...(recommendations?.stocks?.recommendations || []).map((r) => ({ ...r, source: 'Stocks' })),
    ...(recommendations?.mutual_funds?.recommendations || []).map((r) => ({ ...r, source: 'Funds' })),
  ].filter((r) => r.title || r.message);

  const stockCount = summary?.stocks?.count || 0;
  const mfCount = summary?.mutual_funds?.count || 0;
  if (!recs.length && stockCount + mfCount === 0) return null;

  return (
    <section className="mb-8">
      <div className="flex flex-wrap items-end justify-between gap-3 mb-4">
        <div className="flex items-center gap-2">
          <Sparkles className="w-5 h-5 text-indigo-600" />
          <div>
            <h3 className="text-lg font-bold text-slate-900">Next moves</h3>
            <p className="text-xs text-slate-500">From your uploaded stocks and funds — not a generic sector checklist</p>
          </div>
        </div>
        {(stockCount || mfCount) ? (
          <div className="flex flex-wrap gap-2 text-xs">
            {stockCount > 0 && (
              <span className="px-2.5 py-1 rounded-full bg-slate-100 text-slate-700 font-medium">
                {stockCount} stocks · {inr(summary.stocks.current)}
              </span>
            )}
            {mfCount > 0 && (
              <span className="px-2.5 py-1 rounded-full bg-slate-100 text-slate-700 font-medium">
                {mfCount} funds · {inr(summary.mutual_funds.current)}
              </span>
            )}
          </div>
        ) : null}
      </div>

      {recs.length === 0 ? (
        <p className="text-sm text-slate-500 bg-white border border-slate-200 rounded-2xl p-4">
          Portfolio saved. Upload again after a few more holdings to get specific actions.
        </p>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-3">
          {recs.slice(0, 6).map((rec, idx) => {
            const style = STYLES[rec.type] || STYLES.review;
            const Icon = style.Icon;
            return (
              <article key={idx} className={cn('rounded-2xl border p-4 shadow-sm', style.wrap)}>
                <div className="flex items-center justify-between gap-2 mb-3">
                  <span className={cn('inline-flex items-center gap-1.5 text-[11px] font-semibold px-2 py-0.5 rounded-full', style.iconWrap)}>
                    <Icon className="w-3 h-3" />
                    {style.label}
                  </span>
                  <span className="text-[10px] font-semibold uppercase tracking-wide text-slate-500">{rec.source}</span>
                </div>
                <h4 className="text-sm font-bold text-slate-900 leading-snug">{rec.title || rec.message}</h4>
                {rec.title && rec.message && (
                  <p className="text-xs text-slate-600 mt-1.5 leading-relaxed">{rec.message}</p>
                )}
              </article>
            );
          })}
        </div>
      )}
    </section>
  );
}
