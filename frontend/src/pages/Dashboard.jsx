import { useEffect, useState } from 'react'
import { api, fmt, fmtRelative } from '../services/api'
import { Badge, PriorityBadge, StatCard, PageHeader, Spinner, EmptyState } from '../components/ui'
import Icon from '../components/Icon'
import {
  ResponsiveContainer, PieChart, Pie, Cell, Tooltip, Legend,
  BarChart, Bar, XAxis, YAxis, CartesianGrid
} from 'recharts'

const PALETTE = ['#6366f1', '#0ea5e9', '#f59e0b', '#10b981', '#ef4444', '#8b5cf6', '#06b6d4', '#f97316', '#64748b']

export default function Dashboard() {
  const [data, setData] = useState(null)
  const [error, setError] = useState('')

  useEffect(() => {
    api('/dashboard').then(setData).catch((e) => setError(e.message))
  }, [])

  if (error) return <div className="card p-6 text-rose-600 bg-rose-50 dark:bg-rose-950/20">{error}</div>
  if (!data) return <Spinner />

  const { role, counts, by_status, by_priority, by_severity, by_module, by_developer, developer_workload, recent } = data

  return (
    <div className="space-y-7">
      {/* Header */}
      <PageHeader
        title={`${role.charAt(0).toUpperCase() + role.slice(1)} Dashboard`}
        subtitle="Real-time software telemetry, defect metrics, and lifecycle progress connected to live database."
        badge={
          <span className="rounded-full px-3 py-1 text-xs font-bold uppercase tracking-wider bg-brand-500/15 text-brand-600 dark:text-brand-400 border border-brand-500/30">
            Role: {role}
          </span>
        }
        actions={
          <div className="flex items-center gap-2">
            <a href="#/report" className="btn-primary">
              <Icon name="plus" className="w-4 h-4" /> Report Issue
            </a>
            {role === 'admin' && (
              <a href="#/reports" className="btn-secondary">
                <Icon name="chart" className="w-4 h-4" /> Reports &amp; Exports
              </a>
            )}
          </div>
        }
      />

      {/* Role-Specific Metric Cards */}
      {role === 'admin' && <AdminMetrics counts={counts} />}
      {role === 'developer' && <DeveloperMetrics counts={counts} />}
      {role === 'tester' && <TesterMetrics counts={counts} />}
      {role === 'reporter' && <ReporterMetrics counts={counts} />}

      {/* Main Dashboard Content Based on Role */}
      {role === 'admin' && (
        <>
          {/* Charts Row */}
          <div className="grid md:grid-cols-2 xl:grid-cols-3 gap-5">
            <ChartCard title="Bugs by Status">
              <PieDonut data={by_status} />
            </ChartCard>
            <ChartCard title="Bugs by Priority">
              <PieDonut data={by_priority} />
            </ChartCard>
            <ChartCard title="Bugs by Severity">
              <Bars data={by_severity} color="#ef4444" />
            </ChartCard>
            <ChartCard title="Hotspot Modules">
              <Bars data={by_module} color="#0ea5e9" />
            </ChartCard>
            <ChartCard title="Bugs Assigned per Developer">
              <Bars data={by_developer} color="#6366f1" />
            </ChartCard>

            {/* Developer Workload Summary */}
            <div className="card p-5 flex flex-col">
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-sm font-bold text-slate-800 dark:text-slate-200">Developer Workload</h3>
                <a href="#/developers" className="text-xs text-brand-600 dark:text-brand-400 hover:underline">View all</a>
              </div>
              <div className="overflow-x-auto flex-1">
                <table className="w-full text-left text-xs">
                  <thead>
                    <tr className="border-b border-slate-100 dark:border-slate-800 text-slate-400">
                      <th className="pb-2 font-semibold">Developer</th>
                      <th className="pb-2 font-semibold text-center">Active</th>
                      <th className="pb-2 font-semibold text-center">Critical</th>
                      <th className="pb-2 font-semibold text-center">Fixed</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                    {(developer_workload || []).map((dev) => (
                      <tr key={dev.id} className="hover:bg-slate-50/50 dark:hover:bg-slate-800/40">
                        <td className="py-2.5 font-medium text-slate-700 dark:text-slate-200">{dev.name}</td>
                        <td className="py-2.5 text-center">
                          <span className="rounded-full px-2 py-0.5 font-bold bg-blue-50 text-blue-700 dark:bg-blue-950/40 dark:text-blue-300">
                            {dev.in_progress}
                          </span>
                        </td>
                        <td className="py-2.5 text-center">
                          <span className="rounded-full px-2 py-0.5 font-bold bg-rose-50 text-rose-700 dark:bg-rose-950/40 dark:text-rose-300">
                            {dev.critical}
                          </span>
                        </td>
                        <td className="py-2.5 text-center">
                          <span className="rounded-full px-2 py-0.5 font-bold bg-emerald-50 text-emerald-700 dark:bg-emerald-950/40 dark:text-emerald-300">
                            {dev.fixed}
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        </>
      )}

      {/* Developer View Details */}
      {role === 'developer' && (
        <div className="grid xl:grid-cols-3 gap-6">
          <div className="xl:col-span-2 space-y-4">
            <div className="flex items-center justify-between">
              <h2 className="text-base font-bold text-slate-800 dark:text-white flex items-center gap-2">
                <Icon name="terminal" className="w-5 h-5 text-brand-600" /> My Current Sprint Tasks
              </h2>
              <a href="#/my-bugs" className="text-xs text-brand-600 hover:underline">View all assigned</a>
            </div>
            <RecentBugTable bugs={recent} emptyMsg="No active bugs assigned to you right now. Great job!" />
          </div>
          <div>
            <ChartCard title="My Work by Priority">
              <PieDonut data={by_priority} />
            </ChartCard>
          </div>
        </div>
      )}

      {/* Tester View Details */}
      {role === 'tester' && (
        <div className="grid xl:grid-cols-3 gap-6">
          <div className="xl:col-span-2 space-y-4">
            <div className="flex items-center justify-between">
              <h2 className="text-base font-bold text-slate-800 dark:text-white flex items-center gap-2">
                <Icon name="shield" className="w-5 h-5 text-emerald-600" /> Bugs Awaiting Testing &amp; Verification
              </h2>
              <span className="text-xs text-slate-400">Fixed bugs requiring test verification</span>
            </div>
            <RecentBugTable bugs={recent} emptyMsg="No bugs are currently awaiting testing." />
          </div>
          <div>
            <ChartCard title="Overall Defect Statuses">
              <PieDonut data={by_status} />
            </ChartCard>
          </div>
        </div>
      )}

      {/* Reporter View Details */}
      {role === 'reporter' && (
        <div className="grid xl:grid-cols-3 gap-6">
          <div className="xl:col-span-2 space-y-4">
            <div className="flex items-center justify-between">
              <h2 className="text-base font-bold text-slate-800 dark:text-white flex items-center gap-2">
                <Icon name="timeline" className="w-5 h-5 text-brand-600" /> My Submitted Issues &amp; Progress Timeline
              </h2>
              <a href="#/bugs" className="text-xs text-brand-600 hover:underline">Browse all reports</a>
            </div>
            <RecentBugTable bugs={recent} emptyMsg="You haven't reported any bugs yet. Click 'Report Issue' to submit your first report!" />
          </div>
          <div className="space-y-5">
            <div className="card p-6 bg-gradient-to-br from-brand-900 via-indigo-950 to-slate-900 text-white">
              <h3 className="font-extrabold text-lg mb-2">Need to report a problem?</h3>
              <p className="text-xs text-slate-300 leading-relaxed mb-4">
                Submit screenshots, reproduction steps, and system environment info. Our automated AI engine calculates the optimal priority score immediately.
              </p>
              <a href="#/report" className="btn bg-white text-slate-900 hover:bg-slate-100 font-bold text-xs py-2 px-4 shadow-md inline-flex items-center gap-2">
                <Icon name="plus" className="w-4 h-4" /> Report Software Bug
              </a>
            </div>
            <ChartCard title="My Reports by Status">
              <PieDonut data={by_status} />
            </ChartCard>
          </div>
        </div>
      )}

      {/* Recent Activity Table for Admin */}
      {role === 'admin' && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-base font-bold text-slate-800 dark:text-white flex items-center gap-2">
              <Icon name="clock" className="w-5 h-5 text-slate-500" /> Recent Bug Reports &amp; Status Changes
            </h2>
            <a href="#/bugs" className="text-xs text-brand-600 dark:text-brand-400 hover:underline">View All Bugs →</a>
          </div>
          <RecentBugTable bugs={recent} emptyMsg="No bug reports yet." />
        </div>
      )}
    </div>
  )
}

function AdminMetrics({ counts }) {
  return (
    <div className="grid grid-cols-2 md:grid-cols-4 xl:grid-cols-8 gap-3.5">
      <StatCard label="Total Bugs" value={counts.total_bugs} icon="list" color="#6366f1" />
      <StatCard label="Open Bugs" value={counts.open_bugs} icon="flag" color="#0ea5e9" />
      <StatCard label="In Progress" value={counts.in_progress_bugs} icon="refresh" color="#d97706" />
      <StatCard label="Resolved" value={counts.resolved_bugs} icon="check-circle" color="#10b981" />
      <StatCard label="Closed" value={counts.closed_bugs} icon="check" color="#475569" />
      <StatCard label="Critical" value={counts.critical_bugs} icon="x-circle" color="#ef4444" />
      <StatCard label="Reopened" value={counts.reopened_bugs} icon="alert" color="#f59e0b" />
      <StatCard label="Unassigned" value={counts.unassigned_bugs} icon="user" color="#8b5cf6" />
    </div>
  )
}

function DeveloperMetrics({ counts }) {
  return (
    <div className="grid grid-cols-2 md:grid-cols-3 xl:grid-cols-5 gap-4">
      <StatCard label="Assigned to Me" value={counts.assigned_bugs} icon="user" color="#6366f1" />
      <StatCard label="Pending Tasks" value={counts.pending_tasks} icon="clock" color="#0ea5e9" />
      <StatCard label="In Progress" value={counts.in_progress_bugs} icon="refresh" color="#d97706" />
      <StatCard label="Fixed by Me" value={counts.fixed_bugs} icon="check-circle" color="#10b981" />
      <StatCard label="Critical Issues" value={counts.critical_bugs} icon="x-circle" color="#ef4444" />
    </div>
  )
}

function TesterMetrics({ counts }) {
  return (
    <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
      <StatCard label="Awaiting Verification" value={counts.awaiting_verification} icon="clock" color="#06b6d4" />
      <StatCard label="Verified Bugs" value={counts.verified_bugs} icon="check-circle" color="#10b981" />
      <StatCard label="Reopened Bugs" value={counts.reopened_bugs} icon="alert" color="#ef4444" />
      <StatCard label="My Tested Issues" value={counts.testing_history} icon="shield" color="#6366f1" />
    </div>
  )
}

function ReporterMetrics({ counts }) {
  return (
    <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
      <StatCard label="My Reported Bugs" value={counts.my_reported_bugs} icon="list" color="#6366f1" />
      <StatCard label="Pending Triage" value={counts.pending_reports} icon="clock" color="#0ea5e9" />
      <StatCard label="Under Investigation" value={counts.under_investigation} icon="refresh" color="#d97706" />
      <StatCard label="Resolved Reports" value={counts.resolved_reports} icon="check-circle" color="#10b981" />
    </div>
  )
}

function RecentBugTable({ bugs, emptyMsg }) {
  if (!bugs || bugs.length === 0) {
    return <div className="card p-6"><EmptyState message={emptyMsg} /></div>
  }
  return (
    <div className="card overflow-hidden">
      <div className="overflow-x-auto">
        <table className="w-full text-left text-xs">
          <thead>
            <tr className="th">
              <th className="py-3 px-4">Bug</th>
              <th className="py-3 px-4">Module</th>
              <th className="py-3 px-4">Priority</th>
              <th className="py-3 px-4">Status</th>
              <th className="py-3 px-4">Assignee</th>
              <th className="py-3 px-4">Updated</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
            {bugs.map((b) => (
              <tr key={b.id} className="hover:bg-slate-50/80 dark:hover:bg-slate-800/50 transition">
                <td className="td font-medium max-w-xs">
                  <a href={`#/bugs/${b.id}`} className="hover:text-brand-600 dark:hover:text-brand-400 block truncate">
                    <span className="font-mono text-slate-400 mr-1.5">#{b.id}</span>
                    <span className="text-slate-900 dark:text-white font-semibold">{b.title}</span>
                  </a>
                </td>
                <td className="td text-slate-500 dark:text-slate-400">{b.module || 'Unspecified'}</td>
                <td className="td"><PriorityBadge value={b.priority} /></td>
                <td className="td"><Badge value={b.status} /></td>
                <td className="td text-slate-600 dark:text-slate-300">
                  {b.assigned_name ? (
                    <span className="inline-flex items-center gap-1.5">
                      <span className="w-5 h-5 rounded-full bg-brand-100 dark:bg-brand-950 text-brand-700 dark:text-brand-300 flex items-center justify-center text-[10px] font-bold">
                        {b.assigned_name[0]}
                      </span>
                      {b.assigned_name}
                    </span>
                  ) : (
                    <span className="text-slate-400 italic">Unassigned</span>
                  )}
                </td>
                <td className="td text-slate-400 whitespace-nowrap">{fmtRelative(b.updated_at || b.created_at)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}

function ChartCard({ title, children }) {
  return (
    <div className="card p-5 flex flex-col">
      <h3 className="text-sm font-bold text-slate-800 dark:text-slate-200 mb-4">{title}</h3>
      <div className="h-56 w-full">{children}</div>
    </div>
  )
}

function PieDonut({ data }) {
  if (!data || data.length === 0) return <EmptyState message="No data available yet." />
  return (
    <ResponsiveContainer width="100%" height="100%">
      <PieChart>
        <Pie
          data={data}
          dataKey="value"
          nameKey="key"
          innerRadius={48}
          outerRadius={78}
          paddingAngle={3}
          stroke="transparent"
        >
          {data.map((_, i) => (
            <Cell key={i} fill={PALETTE[i % PALETTE.length]} />
          ))}
        </Pie>
        <Tooltip
          contentStyle={{
            backgroundColor: '#0f172a',
            borderColor: '#334155',
            borderRadius: '8px',
            color: '#fff',
            fontSize: '12px'
          }}
        />
        <Legend wrapperStyle={{ fontSize: '11px', paddingTop: '8px' }} />
      </PieChart>
    </ResponsiveContainer>
  )
}

function Bars({ data, color = '#6366f1' }) {
  if (!data || data.length === 0) return <EmptyState message="No data available yet." />
  return (
    <ResponsiveContainer width="100%" height="100%">
      <BarChart data={data} margin={{ top: 5, right: 5, left: -22, bottom: 5 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" opacity={0.5} vertical={false} />
        <XAxis
          dataKey="key"
          tick={{ fontSize: 10, fill: '#64748b' }}
          interval={0}
          angle={-14}
          textAnchor="end"
          height={42}
        />
        <YAxis tick={{ fontSize: 10, fill: '#64748b' }} allowDecimals={false} />
        <Tooltip
          contentStyle={{
            backgroundColor: '#0f172a',
            borderColor: '#334155',
            borderRadius: '8px',
            color: '#fff',
            fontSize: '12px'
          }}
        />
        <Bar dataKey="value" name="Bugs" fill={color} radius={[4, 4, 0, 0]} maxBarSize={32} />
      </BarChart>
    </ResponsiveContainer>
  )
}
