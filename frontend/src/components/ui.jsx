// Polished SaaS UI components with Dark Mode and Jira/Linear aesthetics
import Icon from './Icon'

export const KIND_COLORS = {
  status: {
    reported: '#64748b',
    triaged: '#6366f1',
    assigned: '#2563eb',
    in_progress: '#d97706',
    fixed: '#10b981',
    testing: '#06b6d4',
    verified: '#059669',
    closed: '#475569',
    reopened: '#e11d48',
    rejected: '#dc2626',
    duplicate: '#8b5cf6',
    cannot_reproduce: '#71717a'
  },
  priority: {
    Critical: '#dc2626',
    High: '#ea580c',
    Medium: '#ca8a04',
    Low: '#16a34a'
  },
  severity: {
    Critical: '#dc2626',
    High: '#ea580c',
    Medium: '#ca8a04',
    Low: '#65a30d'
  },
  impact: {
    High: '#dc2626',
    Medium: '#ca8a04',
    Low: '#16a34a'
  },
  role: {
    admin: '#6366f1',
    developer: '#0ea5e9',
    tester: '#10b981',
    reporter: '#f59e0b'
  },
  resolution: {
    Fixed: '#059669',
    "Won't Fix": '#64748b',
    Invalid: '#64748b',
    Duplicate: '#ca8a04',
    'Works For Me': '#0284c7'
  }
}

export function Badge({ value, kind = 'status' }) {
  if (value === null || value === undefined || value === '') return <span className="text-slate-400 text-xs">—</span>
  const label = kind === 'status' ? (value || '').replace(/_/g, ' ') : value
  const color = (KIND_COLORS[kind] || {})[value] || '#64748b'
  return (
    <span
      className="inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-xs font-semibold whitespace-nowrap capitalize tracking-wide border shadow-2xs"
      style={{
        backgroundColor: color + '18',
        color: color,
        borderColor: color + '35'
      }}
    >
      <span className="w-1.5 h-1.5 rounded-full" style={{ backgroundColor: color }} />
      {label}
    </span>
  )
}

export function PriorityBadge({ value }) {
  const color = KIND_COLORS.priority[value] || '#64748b'
  return (
    <span
      className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-semibold border shadow-2xs"
      style={{
        backgroundColor: color + '15',
        color: color,
        borderColor: color + '30'
      }}
    >
      <Icon name="flag" className="w-3 h-3" />
      {value || 'Unset'}
    </span>
  )
}

export function StatCard({ label, value, icon, color = '#6366f1', sub, trend }) {
  return (
    <div className="card p-5 flex items-start justify-between gap-4 transition hover:shadow-md hover:border-slate-300 dark:hover:border-slate-700">
      <div className="min-w-0">
        <div className="text-xs font-semibold uppercase tracking-wider text-slate-500 dark:text-slate-400 mb-1">{label}</div>
        <div className="text-3xl font-extrabold text-slate-900 dark:text-white tracking-tight">{value}</div>
        {sub && <div className="text-xs text-slate-400 dark:text-slate-500 mt-1">{sub}</div>}
        {trend && (
          <div className="text-xs text-emerald-600 dark:text-emerald-400 font-medium mt-1.5 flex items-center gap-1">
            <span>↑</span> {trend}
          </div>
        )}
      </div>
      <div
        className="w-11 h-11 rounded-xl flex items-center justify-center shrink-0 shadow-inner"
        style={{ backgroundColor: color + '1a', color: color }}
      >
        <Icon name={icon} className="w-5 h-5" />
      </div>
    </div>
  )
}

export function Modal({ open, onClose, title, children, wide }) {
  if (!open) return null
  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/60 backdrop-blur-xs p-4 animate-fadeIn"
      onClick={onClose}
    >
      <div
        className={`card w-full ${wide ? 'max-w-3xl' : 'max-w-md'} max-h-[88vh] overflow-y-auto shadow-2xl border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900`}
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between border-b border-slate-100 dark:border-slate-800 px-6 py-4 sticky top-0 bg-white dark:bg-slate-900 z-10">
          <h3 className="font-bold text-slate-900 dark:text-white text-base">{title}</h3>
          <button
            onClick={onClose}
            className="p-1 rounded-lg text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-800 transition"
          >
            <Icon name="x" className="w-5 h-5" />
          </button>
        </div>
        <div className="p-6">{children}</div>
      </div>
    </div>
  )
}

export function Spinner() {
  return (
    <div className="flex flex-col items-center justify-center py-20 gap-3">
      <div className="w-8 h-8 border-3 border-brand-600 border-t-transparent rounded-full animate-spin" />
      <span className="text-xs text-slate-400 font-medium">Loading BugTrack...</span>
    </div>
  )
}

export function EmptyState({ message, actionText, onAction, icon = 'box' }) {
  return (
    <div className="flex flex-col items-center justify-center py-16 text-center px-4">
      <div className="w-14 h-14 rounded-2xl bg-slate-100 dark:bg-slate-800 flex items-center justify-center text-slate-400 mb-3">
        <Icon name={icon} className="w-7 h-7" />
      </div>
      <p className="text-sm font-medium text-slate-600 dark:text-slate-300 max-w-sm">{message}</p>
      {actionText && onAction && (
        <button onClick={onAction} className="btn-primary mt-4 text-xs">
          {actionText}
        </button>
      )}
    </div>
  )
}

export function PageHeader({ title, subtitle, actions, badge }) {
  return (
    <div className="flex flex-wrap items-end justify-between gap-4 mb-6">
      <div>
        <div className="flex items-center gap-3">
          <h1 className="text-2xl font-extrabold text-slate-900 dark:text-white tracking-tight">{title}</h1>
          {badge}
        </div>
        {subtitle && <p className="text-sm text-slate-500 dark:text-slate-400 mt-1 max-w-2xl">{subtitle}</p>}
      </div>
      {actions && <div className="flex items-center gap-2.5">{actions}</div>}
    </div>
  )
}
