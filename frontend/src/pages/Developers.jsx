import { useEffect, useState } from 'react'
import { api } from '../services/api'
import { Badge, PageHeader, Spinner, EmptyState } from '../components/ui'

export default function Developers() {
  const [users, setUsers] = useState(null)
  useEffect(() => {
    api('/users').then((d) => setUsers(d.users)).catch(() => {})
  }, [])

  if (!users) return <Spinner />

  const devs = users.filter((u) => u.role === 'developer')

  return (
    <div>
      <PageHeader title="Developers" subtitle="Workload overview — every count is computed live from the database." />
      {devs.length === 0 ? <EmptyState message="No developers yet." /> : (
        <div className="grid md:grid-cols-2 xl:grid-cols-3 gap-4">
          {devs.map((d) => (
            <div key={d.id} className="card p-5">
              <div className="flex items-center gap-3 mb-4">
                <div className="w-11 h-11 rounded-full bg-brand-100 text-brand-700 flex items-center justify-center font-bold">
                  {d.name.split(' ').map((n) => n[0]).join('').slice(0, 2)}
                </div>
                <div className="min-w-0">
                  <div className="font-semibold text-slate-900 truncate">{d.name}</div>
                  <div className="text-xs text-slate-400 truncate">{d.email}</div>
                </div>
              </div>
              <div className="grid grid-cols-3 gap-2 text-center">
                <Mini label="Assigned" value={d.total_bugs} color="#4f46e5" />
                <Mini label="Open" value={d.open_bugs} color="#0ea5e9" />
                <Mini label="Resolved" value={d.resolved_bugs} color="#10b981" />
              </div>
              <div className="mt-4 pt-3 border-t border-slate-100 flex items-center justify-between text-xs text-slate-500">
                <span>Critical open bugs</span>
                <Badge value={String(d.critical_bugs)} kind="severity" />
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

function Mini({ label, value, color }) {
  return (
    <div className="rounded-lg bg-slate-50 border border-slate-100 py-2.5">
      <div className="text-xl font-bold" style={{ color }}>{value}</div>
      <div className="text-[11px] text-slate-400">{label}</div>
    </div>
  )
}
