import { useEffect, useState } from 'react'
import { api, downloadFile, toast } from '../services/api'
import { Badge, StatCard, PageHeader, Spinner } from '../components/ui'
import Icon from '../components/Icon'

export default function Reports() {
  const [data, setData] = useState(null)
  const [error, setError] = useState('')
  const [downloadingCsv, setDownloadingCsv] = useState(false)
  const [downloadingPdf, setDownloadingPdf] = useState(false)

  useEffect(() => {
    api('/reports').then(setData).catch((e) => setError(e.message))
  }, [])

  async function handleExportCsv() {
    setDownloadingCsv(true)
    try {
      await downloadFile('/reports/csv', 'bugtrack_audit_report.csv')
      toast('CSV report downloaded successfully')
    } catch (err) {
      toast('Failed to download CSV: ' + err.message, 'error')
    } finally {
      setDownloadingCsv(false)
    }
  }

  async function handleExportPdf() {
    setDownloadingPdf(true)
    try {
      await downloadFile('/reports/pdf', 'bugtrack_executive_report.pdf')
      toast('Executive PDF report downloaded successfully')
    } catch (err) {
      toast('Failed to generate PDF: ' + err.message, 'error')
    } finally {
      setDownloadingPdf(false)
    }
  }

  if (error) return <div className="card p-6 text-rose-600 bg-rose-50 dark:bg-rose-950/20">{error}</div>
  if (!data) return <Spinner />

  const {
    total_bugs, open_bugs, closed_bugs, unassigned, avg_days_open,
    by_status, by_priority, by_severity, by_module, by_developer, resolution_breakdown
  } = data

  return (
    <div className="space-y-6">
      <PageHeader
        title="Quality &amp; Defect Analytics"
        subtitle="Comprehensive engineering audit reports, resolution trends, developer throughput, and export utilities."
        actions={
          <div className="flex items-center gap-2">
            <button
              onClick={handleExportCsv}
              disabled={downloadingCsv}
              className="btn-secondary text-xs font-bold"
            >
              <Icon name="download" className="w-4 h-4 text-slate-500" />
              {downloadingCsv ? 'Generating CSV…' : 'Export CSV'}
            </button>
            <button
              onClick={handleExportPdf}
              disabled={downloadingPdf}
              className="btn-primary text-xs font-bold"
            >
              <Icon name="file" className="w-4 h-4" />
              {downloadingPdf ? 'Compiling PDF…' : 'Export Executive PDF'}
            </button>
          </div>
        }
      />

      {/* KPI Stats */}
      <div className="grid grid-cols-2 md:grid-cols-3 xl:grid-cols-5 gap-4">
        <StatCard label="Total Logged" value={total_bugs} icon="list" color="#6366f1" />
        <StatCard label="Active Open" value={open_bugs} icon="flag" color="#0ea5e9" />
        <StatCard label="Closed Defects" value={closed_bugs} icon="check-circle" color="#10b981" />
        <StatCard label="Unassigned" value={unassigned} icon="user" color="#f59e0b" />
        <StatCard label="Avg Turnaround" value={`${avg_days_open}d`} icon="clock" color="#8b5cf6" sub="Time to resolution" />
      </div>

      {/* Analytics Tables */}
      <div className="grid md:grid-cols-2 xl:grid-cols-3 gap-5">
        <ReportCard title="Distribution by Status" data={by_status} kind="status" />
        <ReportCard title="Breakdown by Priority" data={by_priority} kind="priority" />
        <ReportCard title="Breakdown by Severity" data={by_severity} kind="severity" />
        <ReportCard title="Hotspot Modules (Top 10)" data={by_module} />
        <ReportCard title="Developer Throughput" data={by_developer} />
        <ReportCard title="Resolution Categories" data={resolution_breakdown} kind="resolution" />
      </div>
    </div>
  )
}

function ReportCard({ title, data, kind }) {
  const total = (data || []).reduce((acc, cur) => acc + cur.value, 0)
  return (
    <div className="card p-5 space-y-4">
      <div className="flex items-center justify-between border-b border-slate-100 dark:border-slate-800 pb-3">
        <h3 className="text-sm font-bold text-slate-800 dark:text-slate-200">{title}</h3>
        <span className="text-xs text-slate-400 font-mono">{total} total</span>
      </div>

      <div className="space-y-2">
        {(data || []).map((row, idx) => {
          const pct = total > 0 ? Math.round((row.value / total) * 100) : 0
          return (
            <div key={idx} className="space-y-1">
              <div className="flex items-center justify-between text-xs">
                <span className="font-medium text-slate-700 dark:text-slate-300">
                  {kind ? <Badge value={row.key} kind={kind} /> : (row.key || 'Unspecified')}
                </span>
                <span className="font-mono text-slate-500 font-semibold">
                  {row.value} <span className="text-slate-400 text-[10px]">({pct}%)</span>
                </span>
              </div>
              <div className="h-1.5 rounded-full bg-slate-100 dark:bg-slate-800 overflow-hidden">
                <div
                  className="h-full rounded-full bg-brand-500 transition-all duration-300"
                  style={{ width: `${pct}%` }}
                />
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}
