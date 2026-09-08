import { ChevronUp, ChevronDown } from 'lucide-react';

export function cn(...classes) {
  return classes.filter(Boolean).join(' ');
}

export function TabPanel({ children, k }) {
  return (
    <div key={k} className="animate-fadeIn">
      {children}
    </div>
  );
}

export function SectionTitle({ icon: Icon, color, title, subtitle }) {
  return (
    <div className="flex items-center gap-3 mb-6">
      {Icon && <Icon className={cn('w-6 h-6 flex-shrink-0', color)} />}
      <div>
        <h2 className="text-xl md:text-2xl font-bold text-slate-900">{title}</h2>
        {subtitle && <p className="text-xs md:text-sm text-slate-500">{subtitle}</p>}
      </div>
    </div>
  );
}

export function SummaryCard({ title, value, subtitle, className }) {
  return (
    <div className={cn('bg-white p-4 md:p-6 rounded-2xl shadow-sm border border-slate-200', className)}>
      <p className="text-xs md:text-sm font-medium text-slate-500 mb-1">{title}</p>
      <p className="text-xl md:text-2xl font-bold text-slate-900">₹{(value || 0).toLocaleString('en-IN')}</p>
      {subtitle && <p className="text-xs text-slate-400 mt-1">{subtitle}</p>}
    </div>
  );
}

export function SortableTh({ label, sortKey, current, dir, onSort }) {
  const active = current === sortKey;
  return (
    <th className="px-3 md:px-6 py-3 text-left">
      <button
        type="button"
        onClick={() => onSort(sortKey)}
        className={cn(
          'inline-flex items-center gap-1 text-xs font-semibold uppercase tracking-wide',
          active ? 'text-slate-900' : 'text-slate-500 hover:text-slate-800'
        )}
      >
        {label}
        {active
          ? (dir === 'asc' ? <ChevronUp size={14} /> : <ChevronDown size={14} />)
          : <span className="text-[10px] text-slate-300">↕</span>}
      </button>
    </th>
  );
}

export function DataTable({ children }) {
  return (
    <div className="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-x-auto">
      <table className="w-full text-left min-w-[600px]">{children}</table>
    </div>
  );
}

export function LoadMore({ onClick, loading, remaining }) {
  return (
    <div className="text-center mt-6">
      <button
        type="button"
        onClick={onClick}
        disabled={loading}
        className="px-4 py-2 text-sm font-medium text-indigo-700 bg-indigo-50 rounded-xl hover:bg-indigo-100 disabled:opacity-50 transition-colors"
      >
        {loading ? 'Loading...' : `Load more (${Number(remaining || 0).toLocaleString('en-IN')} remaining)`}
      </button>
    </div>
  );
}

export function EmptyState({ text }) {
  return <p className="text-center text-slate-500 py-12 bg-white rounded-2xl border border-slate-200">{text}</p>;
}

export function SkeletonGrid({ count = 3 }) {
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 md:gap-6">
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

export function SkeletonTable() {
  return <div className="bg-white rounded-2xl border border-slate-200 h-64 animate-pulse" />;
}

export function Badge({ children, color = 'slate' }) {
  const colors = {
    slate: 'bg-slate-100 text-slate-700',
    green: 'bg-emerald-50 text-emerald-700',
    red: 'bg-red-50 text-red-700',
    blue: 'bg-blue-50 text-blue-700',
    purple: 'bg-purple-50 text-purple-700',
    indigo: 'bg-indigo-50 text-indigo-700',
    amber: 'bg-amber-50 text-amber-700',
  };
  return (
    <span className={cn('text-[10px] md:text-xs font-semibold px-2 py-0.5 rounded-md', colors[color])}>
      {children}
    </span>
  );
}

export function MetricRow({ label, value, highlight }) {
  return (
    <div className="flex justify-between items-center py-2 border-b border-slate-50 last:border-0">
      <span className="text-xs md:text-sm text-slate-500">{label}</span>
      <span className={cn('text-xs md:text-sm font-semibold', highlight || 'text-slate-900')}>{value}</span>
    </div>
  );
}

export function fmtNav(value) {
  if (value == null || value === '') return '—';
  const n = Number(value);
  if (Number.isNaN(n)) return '—';
  return n.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 4 });
}

export function fmtPct(value) {
  if (value == null || value === '') return '—';
  const n = Number(value);
  if (Number.isNaN(n)) return '—';
  const cls = n >= 0 ? 'text-emerald-700' : 'text-red-700';
  return <span className={`font-medium ${cls}`}>{n >= 0 ? '+' : ''}{n.toFixed(2)}%</span>;
}

export function fmtNum(value, decimals = 2) {
  if (value == null || value === '') return '—';
  const n = Number(value);
  if (Number.isNaN(n)) return '—';
  return n.toFixed(decimals);
}