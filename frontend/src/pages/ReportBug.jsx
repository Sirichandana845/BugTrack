import { useEffect, useState } from 'react'
import { api, toast } from '../services/api'
import { Badge, PriorityBadge, PageHeader } from '../components/ui'
import Icon from '../components/Icon'

const MODULE_OPTIONS = [
  'Auth / Login', 'Dashboard', 'Bug Tracker', 'User Management',
  'Reports & Analytics', 'Notifications', 'Settings / Profile',
  'API Gateway', 'Mobile Application', 'UI / UX', 'Database / Storage', 'Other'
]

const OS_OPTIONS = [
  'Windows 11', 'Windows 10', 'macOS Sonoma (14.x)', 'macOS Ventura (13.x)',
  'Ubuntu 24.04 / Linux', 'Android 14', 'Android 13', 'iOS 17', 'iOS 16', 'Other'
]

const DEVICE_OPTIONS = [
  'Google Chrome', 'Mozilla Firefox', 'Apple Safari', 'Microsoft Edge',
  'Mobile Browser (Chrome/Safari)', 'React Native Expo App', 'Desktop App', 'Other'
]

export default function ReportBug() {
  const empty = {
    title: '',
    description: '',
    module: '',
    steps_to_reproduce: '',
    expected_result: '',
    actual_result: '',
    severity: 'Medium',
    impact: 'Medium',
    operating_system: 'Windows 11',
    browser_device: 'Google Chrome',
    app_version: 'v1.0.0'
  }
  const [form, setForm] = useState(empty)
  const [attachment, setAttachment] = useState(null)
  const [attachmentName, setAttachmentName] = useState('')
  const [rec, setRec] = useState(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')

  // Live recommendation preview whenever severity or impact changes
  useEffect(() => {
    if (!form.severity || !form.impact) return
    const t = setTimeout(() => {
      api('/priority-recommend', {
        method: 'POST',
        body: { severity: form.severity, impact: form.impact }
      })
        .then(setRec)
        .catch(() => {})
    }, 150)
    return () => clearTimeout(t)
  }, [form.severity, form.impact])

  const set = (key, value) => setForm((f) => ({ ...f, [key]: value }))

  function onFile(e) {
    const file = e.target.files && e.target.files[0]
    if (!file) return
    if (file.size > 8 * 1024 * 1024) {
      toast('Attachment must be under 8 MB', 'error')
      e.target.value = ''
      return
    }
    const reader = new FileReader()
    reader.onload = () => setAttachment(reader.result)
    reader.readAsDataURL(file)
    setAttachmentName(file.name)
  }

  function removeFile() {
    setAttachment(null)
    setAttachmentName('')
  }

  async function submit(e) {
    e.preventDefault()
    if (!form.title.trim()) {
      setError('Bug title is required.')
      return
    }
    setBusy(true)
    setError('')
    try {
      const data = await api('/bugs', {
        method: 'POST',
        body: { ...form, attachment }
      })
      toast(`Bug #${data.bug.id} reported — Recommended Priority: ${data.recommendation.recommended_priority}`)
      window.location.hash = `#/bugs/${data.bug.id}`
    } catch (err) {
      setError(err.message)
      toast('Failed to report bug', 'error')
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="space-y-6">
      <PageHeader
        title="Report Software Problem"
        subtitle="Log a new defect into the tracking system with reproduction steps, environment telemetry, and automatic priority calculation."
      />

      <form onSubmit={submit} className="grid xl:grid-cols-3 gap-6">
        {/* Left 2 Cols: Form Fields */}
        <div className="xl:col-span-2 space-y-5">
          {/* Section 1: Overview */}
          <div className="card p-6 space-y-4">
            <h3 className="text-sm font-bold text-slate-900 dark:text-white uppercase tracking-wider flex items-center gap-2">
              <Icon name="bug" className="w-4 h-4 text-brand-600" /> Defect Overview
            </h3>

            <div>
              <label className="label">Bug Title *</label>
              <input
                className="input font-medium"
                value={form.title}
                required
                onChange={(e) => set('title', e.target.value)}
                placeholder="e.g. Session expires unexpectedly during card payment submission"
              />
            </div>

            <div>
              <label className="label">Detailed Description</label>
              <textarea
                className="input min-h-[90px]"
                value={form.description}
                onChange={(e) => set('description', e.target.value)}
                placeholder="Explain the symptom, where it occurred, and who is affected..."
              />
            </div>

            <div className="grid md:grid-cols-3 gap-4 pt-1">
              <div>
                <label className="label">Application / Module</label>
                <select
                  className="input"
                  value={form.module}
                  onChange={(e) => set('module', e.target.value)}
                >
                  <option value="">Select module…</option>
                  {MODULE_OPTIONS.map((m) => (
                    <option key={m} value={m}>{m}</option>
                  ))}
                </select>
              </div>

              <div>
                <label className="label">Severity (Technical)</label>
                <select
                  className="input"
                  value={form.severity}
                  onChange={(e) => set('severity', e.target.value)}
                >
                  {['Critical', 'High', 'Medium', 'Low'].map((s) => (
                    <option key={s} value={s}>{s}</option>
                  ))}
                </select>
              </div>

              <div>
                <label className="label">Impact (Business)</label>
                <select
                  className="input"
                  value={form.impact}
                  onChange={(e) => set('impact', e.target.value)}
                >
                  {['High', 'Medium', 'Low'].map((s) => (
                    <option key={s} value={s}>{s}</option>
                  ))}
                </select>
              </div>
            </div>
          </div>

          {/* Section 2: Environment & Device Telemetry */}
          <div className="card p-6 space-y-4">
            <h3 className="text-sm font-bold text-slate-900 dark:text-white uppercase tracking-wider flex items-center gap-2">
              <Icon name="laptop" className="w-4 h-4 text-brand-600" /> Environment Telemetry
            </h3>

            <div className="grid md:grid-cols-3 gap-4">
              <div>
                <label className="label">Operating System</label>
                <select
                  className="input"
                  value={form.operating_system}
                  onChange={(e) => set('operating_system', e.target.value)}
                >
                  {OS_OPTIONS.map((os) => (
                    <option key={os} value={os}>{os}</option>
                  ))}
                </select>
              </div>

              <div>
                <label className="label">Browser / Device</label>
                <select
                  className="input"
                  value={form.browser_device}
                  onChange={(e) => set('browser_device', e.target.value)}
                >
                  {DEVICE_OPTIONS.map((dev) => (
                    <option key={dev} value={dev}>{dev}</option>
                  ))}
                </select>
              </div>

              <div>
                <label className="label">Application Version</label>
                <input
                  className="input"
                  value={form.app_version}
                  placeholder="e.g. v2.1.0"
                  onChange={(e) => set('app_version', e.target.value)}
                />
              </div>
            </div>
          </div>

          {/* Section 3: Reproduction Details */}
          <div className="card p-6 space-y-4">
            <h3 className="text-sm font-bold text-slate-900 dark:text-white uppercase tracking-wider flex items-center gap-2">
              <Icon name="code" className="w-4 h-4 text-brand-600" /> Reproduction Details
            </h3>

            <div>
              <label className="label">Steps to Reproduce</label>
              <textarea
                className="input min-h-[90px] font-mono text-xs"
                value={form.steps_to_reproduce}
                onChange={(e) => set('steps_to_reproduce', e.target.value)}
                placeholder={'1. Navigate to /checkout\n2. Fill card details\n3. Click Submit button\n4. Observe 504 timeout error'}
              />
            </div>

            <div className="grid md:grid-cols-2 gap-4">
              <div>
                <label className="label">Expected Result</label>
                <textarea
                  className="input min-h-[75px]"
                  value={form.expected_result}
                  onChange={(e) => set('expected_result', e.target.value)}
                  placeholder="Confirmation modal with order ID should appear"
                />
              </div>
              <div>
                <label className="label">Actual Result</label>
                <textarea
                  className="input min-h-[75px]"
                  value={form.actual_result}
                  onChange={(e) => set('actual_result', e.target.value)}
                  placeholder="Screen freezes and network console throws 504 Gateway Timeout"
                />
              </div>
            </div>

            {/* Screenshot Attachment */}
            <div>
              <label className="label">Screenshot or Evidence Attachment (max 8 MB)</label>
              {attachment ? (
                <div className="flex items-center gap-3 p-3 rounded-lg border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-800/60">
                  <img
                    src={attachment}
                    alt="Preview"
                    className="w-14 h-14 object-cover rounded-md border border-slate-300 dark:border-slate-700"
                  />
                  <div className="min-w-0 flex-1">
                    <div className="text-xs font-semibold text-slate-800 dark:text-slate-200 truncate">{attachmentName || 'Attachment image'}</div>
                    <div className="text-[11px] text-emerald-600 dark:text-emerald-400">Ready to upload</div>
                  </div>
                  <button
                    type="button"
                    onClick={removeFile}
                    className="p-1.5 rounded-lg text-slate-400 hover:text-rose-600 hover:bg-slate-100 dark:hover:bg-slate-700"
                  >
                    <Icon name="x" className="w-4 h-4" />
                  </button>
                </div>
              ) : (
                <label className="flex flex-col items-center justify-center p-6 rounded-xl border-2 border-dashed border-slate-300 dark:border-slate-700 hover:border-brand-500 dark:hover:border-brand-400 bg-white dark:bg-slate-900 cursor-pointer transition group">
                  <Icon name="image" className="w-8 h-8 text-slate-400 group-hover:text-brand-600 mb-2 transition" />
                  <span className="text-xs font-semibold text-slate-700 dark:text-slate-300">Click to upload screenshot or drag and drop</span>
                  <span className="text-[11px] text-slate-400 mt-1">PNG, JPG, GIF, WebP (up to 8 MB)</span>
                  <input type="file" accept="image/*" className="hidden" onChange={onFile} />
                </label>
              )}
            </div>
          </div>

          {error && (
            <div className="rounded-lg bg-rose-50 dark:bg-rose-950/40 border border-rose-200 dark:border-rose-900 text-rose-700 dark:text-rose-300 text-sm p-4 flex items-center gap-3">
              <Icon name="alert" className="w-5 h-5 shrink-0" />
              <span>{error}</span>
            </div>
          )}

          {/* Form Actions */}
          <div className="flex items-center gap-3 pt-2">
            <button className="btn-primary px-7 py-2.5 font-bold" disabled={busy}>
              {busy ? 'Submitting to BugTrack…' : 'Submit Defect Report'}
            </button>
            <a href="#/bugs" className="btn-secondary py-2.5">Cancel</a>
            <span className="text-xs text-slate-400 ml-auto hidden sm:inline">
              Lifecycle status starts at <b>Reported</b>
            </span>
          </div>
        </div>

        {/* Right Col: Live Recommendation Card */}
        <div>
          <div className="card p-6 sticky top-20 shadow-lg border-brand-200/50 dark:border-brand-900/30">
            <div className="flex items-center gap-2 mb-3 pb-3 border-b border-slate-100 dark:border-slate-800">
              <div className="w-7 h-7 rounded-lg bg-brand-500/15 text-brand-600 dark:text-brand-400 flex items-center justify-center">
                <Icon name="flag" className="w-4 h-4" />
              </div>
              <div>
                <h3 className="text-sm font-bold text-slate-900 dark:text-white">Priority Recommendation</h3>
                <span className="text-[11px] text-slate-400">Intelligent Rule Engine</span>
              </div>
            </div>

            {rec ? (
              <div className="space-y-4">
                <div>
                  <div className="text-xs text-slate-500 dark:text-slate-400 mb-1">Calculated Priority:</div>
                  <div className="flex items-center gap-2">
                    <PriorityBadge value={rec.recommended_priority} />
                    <span className="text-xs text-slate-400 font-mono">({rec.severity} + {rec.impact})</span>
                  </div>
                </div>

                <div className="rounded-xl p-3.5 bg-slate-50 dark:bg-slate-800/80 border border-slate-200/70 dark:border-slate-700/60 text-xs text-slate-700 dark:text-slate-300 leading-relaxed">
                  <div className="font-semibold text-slate-900 dark:text-white mb-1 flex items-center gap-1.5">
                    <Icon name="terminal" className="w-3.5 h-3.5 text-brand-600" /> Explanation:
                  </div>
                  {rec.explanation}
                </div>

                <div className="grid grid-cols-2 gap-2.5 text-xs">
                  <div className="rounded-lg border border-slate-200 dark:border-slate-800 p-2.5">
                    <div className="text-slate-400 mb-1">Severity Input</div>
                    <Badge value={rec.severity} kind="severity" />
                  </div>
                  <div className="rounded-lg border border-slate-200 dark:border-slate-800 p-2.5">
                    <div className="text-slate-400 mb-1">Impact Input</div>
                    <Badge value={rec.impact} kind="impact" />
                  </div>
                </div>
              </div>
            ) : (
              <p className="text-xs text-slate-400">Select Severity and Impact to view the live priority score.</p>
            )}

            <div className="mt-5 pt-4 border-t border-slate-100 dark:border-slate-800 text-[11px] text-slate-400 space-y-2">
              <div className="font-semibold text-slate-700 dark:text-slate-300">Decision Matrix Logic:</div>
              <ul className="space-y-1 list-disc list-inside text-[11px]">
                <li>Critical + High → <b>Critical</b></li>
                <li>High + High / Critical + Med → <b>High</b></li>
                <li>Medium + Medium → <b>Medium</b></li>
                <li>Low + Low → <b>Low</b></li>
              </ul>
              <div className="text-[10px] text-slate-400 pt-1">
                *Admins can override the priority rating post-submission.
              </div>
            </div>
          </div>
        </div>
      </form>
    </div>
  )
}
