import { useEffect, useState, useCallback } from 'react'
import { api, fmtDate, fmtRelative } from '../services/api'
import { Badge, PriorityBadge, PageHeader, Spinner, EmptyState } from '../components/ui'
import Icon from '../components/Icon'

const STATUS_OPTIONS = [
  'reported', 'triaged', 'assigned', 'in_progress', 'fixed',
  'testing', 'verified', 'closed', 'reopened',
  'rejected', 'duplicate', 'cannot_reproduce'
]
const PRIO_OPTIONS = ['Critical', 'High', 'Medium', 'Low']
const SEV_OPTIONS = ['Critical', 'High', 'Medium', 'Low']
const MODULE_OPTIONS = [
  'Auth / Login', 'Dashboard', 'Bug Tracker', 'User Management',
  'Reports & Analytics', 'Notifications', 'Settings / Profile',
  'API Gateway', 'Mobile Application', 'UI / UX', 'Database / Storage', 'Other'
]

export default function BugList({ assignedMe, reportedMe }) {
  const [bugs, setBugs] = useState(null)
  const [developers, setDevelopers] = useState([])
  const [error, setError] = useState('')
  const [filters, setFilters] = useState({
    search: '',
    status: '',
    priority: '',
    severity: '',
    module: '',
    developer: '',
    sort: 'created_at',
    order: 'desc'
  })
  const [debounced, setDebounced] = useState('')

  useEffect(() => {
    const t = setTimeout(() => setDebounced(filters.search), 250)
    return () => clearTimeout(t)
  }, [filters.search])

  const load = useCallback(() => {
    const params = new URLSearchParams()
    if (debounced) params.set('search', debounced)
    if (filters.status) params.set('status', filters.status)
    if (filters.priority) params.set('priority', filters.priority)
    if (filters.severity) params.set('severity', filters.severity)
    if (filters.module) params.set('module', filters.module)
    if (filters.developer) params.set('developer', filters.developer)
    if (filters.sort) params.set('sort', filters.sort)
    if (filters.order) params.set('order', filters.order)
    if (assignedMe) params.set('assigned', 'me')
    if (reportedMe) params.set('reporter', 'me')

    const qs = params.toString()
    api('/bugs' + (qs ? '?' + qs : ''))
      .then(setBugs)
      .catch((e) => setError(e.message))
  }, [debounced, filters, assignedMe, reportedMe])

  useEffect(load, [load])

  useEffect(() => {
    api('/developers').then((d) => setDevelopers(d.developers)).catch(() => {})
  }, [])

  const set = (key, value) => setFilters((f) => ({ ...f, [key]: value }))
  const resetFilters = () => setFilters({
    search: '', status: '', priority: '', severity: '', module: '', developer: '', sort: 'created_at', order: 'desc'
  })

  const hasActiveFilters = Boolean(
    filters.search || filters.status || filters.priority || filters.severity || filters.module || filters.developer
  )

  const title = assignedMe ? 'My Assigned Bugs' : reportedMe ? 'My Reported Bugs' : 'Bug Issues & Tracking'
  const subtitle = assignedMe
    ? 'Viewing issues assigned specifically to you. Start work or submit fixes.'
    : reportedMe
    ? 'Track issues you have submitted to the engineering team.'
    : 'Complete registry of software defects with live SQL querying, multi-dimensional filters, and sorting.'

  return (
    <div className="space-y-5">
      <PageHeader
        title={title}
        subtitle={subtitle}
        actions={
          <a href="#/report" className="btn-primary">
            <Icon name="plus" className="w-4 h-4" /> Report New Bug
          </a>
        }
      />

      {/* Filter Toolbar */}
      <div className="card p-4 space-y-3 shadow-xs">
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-6 gap-2.5">
          {/* Search */}
          <div className="lg:col-span-2 relative">
            <Icon name="search" className="w-4 h-4 absolute left-3 top-2.5 text-slate-400" />
            <input
              className="input pl-9"
              placeholder="Search by title, description, or #ID..."
              value={filters.search}
              onChange={(e) => set('search', e.target.value)}
            />
          </div>

          {/* Status */}
          <select className="input" value={filters.status} onChange={(e) => set('status', e.target.value)}>
            <option value="">All Statuses</option>
            {STATUS_OPTIONS.map((s) => (
              <option key={s} value={s}>{s.replace(/_/g, ' ')}</option>
            ))}
          </select>

          {/* Priority */}
          <select className="input" value={filters.priority} onChange={(e) => set('priority', e.target.value)}>
            <option value="">All Priorities</option>
            {PRIO_OPTIONS.map((s) => (
              <option key={s} value={s}>{s}</option>
            ))}
          </select>

          {/* Severity */}
          <select className="input" value={filters.severity} onChange={(e) => set('severity', e.target.value)}>
            <option value="">All Severities</option>
            {SEV_OPTIONS.map((s) => (
              <option key={s} value={s}>{s}</option>
            ))}
          </select>

          {/* Developer */}
          <select className="input" value={filters.developer} onChange={(e) => set('developer', e.target.value)}>
            <option value="">All Assignees</option>
            {developers.map((d) => (
              <option key={d.id} value={d.id}>{d.name}</option>
            ))}
          </select>
        </div>

        {/* Secondary Row: Module filter + Sorting Controls */}
        <div className="flex flex-wrap items-center justify-between gap-3 pt-1 border-t border-slate-100 dark:border-slate-800 text-xs">
          <div className="flex flex-wrap items-center gap-2">
            <span className="text-slate-400 font-semibold flex items-center gap-1">
              <Icon name="filter" className="w-3.5 h-3.5" /> Module:
            </span>
            <select
              className="input text-xs py-1 px-2.5 w-auto"
              value={filters.module}
              onChange={(e) => set('module', e.target.value)}
            >
              <option value="">All Modules</option>
              {MODULE_OPTIONS.map((m) => (
                <option key={m} value={m}>{m}</option>
              ))}
            </select>

            {hasActiveFilters && (
              <button
                type="button"
                onClick={resetFilters}
                className="text-xs text-brand-600 dark:text-brand-400 hover:underline font-semibold ml-2"
              >
                Clear all filters
              </button>
            )}
          </div>

          <div className="flex items-center gap-2">
            <span className="text-slate-400 font-semibold flex items-center gap-1">
              <Icon name="sort" className="w-3.5 h-3.5" /> Sort:
            </span>
            <select
              className="input text-xs py-1 px-2.5 w-auto"
              value={filters.sort}
              onChange={(e) => set('sort', e.target.value)}
            >
              <option value="created_at">Date Created</option>
              <option value="updated_at">Last Updated</option>
              <option value="priority">Priority</option>
              <option value="status">Status</option>
              <option value="id">Bug ID</option>
              <option value="title">Title</option>
            </select>
            <button
              type="button"
              onClick={() => set('order', filters.order === 'asc' ? 'desc' : 'asc')}
              className="btn-secondary py-1 px-2 text-xs font-semibold"
              title="Toggle sort direction"
            >
              {filters.order.toUpperCase()}
            </button>
          </div>
        </div>
      </div>

      {error && <div className="card p-4 text-rose-600 text-sm">{error}</div>}

      {/* Bug Table */}
      <div className="card overflow-hidden">
        {!bugs ? (
          <Spinner />
        ) : bugs.bugs.length === 0 ? (
          <EmptyState
            message="No bugs match your current filters. Try resetting the search or reporting a new issue."
            actionText={hasActiveFilters ? "Reset Filters" : "Report Bug"}
            onAction={hasActiveFilters ? resetFilters : () => { window.location.hash = '#/report' }}
          />
        ) : (
          <>
            <div className="px-5 py-3 border-b border-slate-100 dark:border-slate-800 text-xs text-slate-500 dark:text-slate-400 flex items-center justify-between bg-slate-50/50 dark:bg-slate-900/50">
              <span className="font-semibold">Showing {bugs.bugs.length} of {bugs.total} issues</span>
              <span className="text-slate-400">Click any row to open full defect details &amp; lifecycle</span>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead>
                  <tr className="th">
                    <th className="py-3 px-4 w-16">ID</th>
                    <th className="py-3 px-4">Summary</th>
                    <th className="py-3 px-4">Module</th>
                    <th className="py-3 px-4">Priority</th>
                    <th className="py-3 px-4">Severity</th>
                    <th className="py-3 px-4">Status</th>
                    <th className="py-3 px-4">Assignee</th>
                    <th className="py-3 px-4">Reporter</th>
                    <th className="py-3 px-4 text-right">Updated</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                  {bugs.bugs.map((b) => (
                    <tr
                      key={b.id}
                      onClick={() => { window.location.hash = `#/bugs/${b.id}` }}
                      className="hover:bg-brand-50/40 dark:hover:bg-slate-800/60 transition cursor-pointer group"
                    >
                      <td className="td font-mono font-bold text-slate-400 group-hover:text-brand-600">
                        #{b.id}
                      </td>
                      <td className="td max-w-sm">
                        <div className="font-semibold text-slate-900 dark:text-white group-hover:text-brand-600 transition truncate">
                          {b.title}
                        </div>
                        {b.description && (
                          <div className="text-[11px] text-slate-400 truncate mt-0.5">
                            {b.description}
                          </div>
                        )}
                      </td>
                      <td className="td text-slate-500 dark:text-slate-400 whitespace-nowrap">
                        <span className="rounded bg-slate-100 dark:bg-slate-800 px-2 py-0.5 text-[11px] font-medium">
                          {b.module || 'Unspecified'}
                        </span>
                      </td>
                      <td className="td whitespace-nowrap"><PriorityBadge value={b.priority} /></td>
                      <td className="td whitespace-nowrap"><Badge value={b.severity} kind="severity" /></td>
                      <td className="td whitespace-nowrap"><Badge value={b.status} /></td>
                      <td className="td whitespace-nowrap text-slate-700 dark:text-slate-300">
                        {b.assigned_name ? (
                          <span className="inline-flex items-center gap-1.5">
                            <span className="w-5 h-5 rounded-full bg-blue-100 dark:bg-blue-950 text-blue-700 dark:text-blue-300 flex items-center justify-center text-[10px] font-bold">
                              {b.assigned_name[0]}
                            </span>
                            {b.assigned_name}
                          </span>
                        ) : (
                          <span className="text-slate-400 italic">Unassigned</span>
                        )}
                      </td>
                      <td className="td text-slate-500 dark:text-slate-400 whitespace-nowrap">
                        {b.creator_name || 'System'}
                      </td>
                      <td className="td text-slate-400 text-right whitespace-nowrap font-mono text-[11px]">
                        {fmtRelative(b.updated_at || b.created_at)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </>
        )}
      </div>
    </div>
  )
}
