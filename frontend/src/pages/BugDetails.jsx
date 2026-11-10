import { useCallback, useEffect, useState } from 'react'
import { api, apiAssetUrl, fmt, fmtRelative, toast } from '../services/api'
import { Badge, PriorityBadge, Modal, Spinner } from '../components/ui'
import Icon from '../components/Icon'

const ACTION_LABELS = {
  triaged: 'Triage Issue',
  assigned: 'Assign Developer',
  in_progress: 'Start Work (In Progress)',
  fixed: 'Mark Fixed (Submit Fix)',
  testing: 'Ready for Testing',
  verified: 'Verify Resolution',
  closed: 'Close Defect',
  reopened: 'Reopen Defect',
  rejected: 'Reject Bug',
  duplicate: 'Mark Duplicate',
  cannot_reproduce: 'Cannot Reproduce'
}

const ACTION_COLORS = {
  in_progress: 'bg-amber-600 hover:bg-amber-700 text-white',
  fixed: 'bg-emerald-600 hover:bg-emerald-700 text-white',
  testing: 'bg-cyan-600 hover:bg-cyan-700 text-white',
  verified: 'bg-teal-600 hover:bg-teal-700 text-white',
  closed: 'bg-slate-700 hover:bg-slate-800 text-white',
  reopened: 'bg-rose-600 hover:bg-rose-700 text-white',
  rejected: 'bg-red-700 hover:bg-red-800 text-white',
  duplicate: 'bg-purple-600 hover:bg-purple-700 text-white',
  cannot_reproduce: 'bg-zinc-600 hover:bg-zinc-700 text-white',
  triaged: 'bg-brand-600 hover:bg-brand-700 text-white'
}

const HISTORY_ICONS = {
  reported: 'plus',
  assigned: 'user',
  unassigned: 'user',
  status_change: 'refresh',
  priority_change: 'flag',
  fixed: 'check-circle',
  comment: 'comment',
  imported: 'box'
}

export default function BugDetails({ bugId }) {
  const [data, setData] = useState(null)
  const [history, setHistory] = useState([])
  const [developers, setDevelopers] = useState([])
  const [error, setError] = useState('')
  const [activeTab, setActiveTab] = useState('comments') // 'comments' | 'history'

  // Modals
  const [assignOpen, setAssignOpen] = useState(false)
  const [priorityOpen, setPriorityOpen] = useState(false)
  const [actionModalOpen, setActionModalOpen] = useState(false)
  const [targetStatus, setTargetStatus] = useState(null)
  const [statusNote, setStatusNote] = useState('')
  const [fixDescription, setFixDescription] = useState('')
  const [lightboxOpen, setLightboxOpen] = useState(false)
  const [commentText, setCommentText] = useState('')
  const [submitting, setSubmitting] = useState(false)

  const load = useCallback(() => {
    Promise.all([
      api(`/bugs/${bugId}`),
      api(`/bugs/${bugId}/history`)
    ])
      .then(([bugData, histData]) => {
        setData(bugData)
        setHistory(histData.history || [])
      })
      .catch((e) => setError(e.message))
  }, [bugId])

  useEffect(load, [load])

  useEffect(() => {
    api('/developers').then((d) => setDevelopers(d.developers)).catch(() => {})
  }, [])

  if (error) return <div className="card p-6 text-rose-600 bg-rose-50 dark:bg-rose-950/20">{error}</div>
  if (!data) return <Spinner />

  const { bug, comments } = data
  const user = JSON.parse(localStorage.getItem('bt_user') || 'null')
  const isAdmin = user && user.role === 'admin'

  function handleActionClick(status) {
    setTargetStatus(status)
    setStatusNote('')
    setFixDescription(bug.fix_description || '')
    if (status === 'fixed' || status === 'reopened' || status === 'cannot_reproduce' || status === 'rejected') {
      setActionModalOpen(true)
    } else {
      executeStatusChange(status, '')
    }
  }

  async function executeStatusChange(status, note, fixDesc = '') {
    setSubmitting(true)
    try {
      await api(`/bugs/${bugId}/status`, {
        method: 'PUT',
        body: { status, note, fix_description: fixDesc || undefined }
      })
      toast(`Status changed to ${status.replace(/_/g, ' ')}`)
      setActionModalOpen(false)
      load()
    } catch (e) {
      toast(e.message, 'error')
    } finally {
      setSubmitting(false)
    }
  }

  async function handleAssign(developerId) {
    try {
      await api(`/bugs/${bugId}/assign`, {
        method: 'PUT',
        body: { developer_id: developerId }
      })
      toast('Assignee updated')
      setAssignOpen(false)
      load()
    } catch (e) {
      toast(e.message, 'error')
    }
  }

  async function handleOverridePriority(priority) {
    try {
      await api(`/bugs/${bugId}`, {
        method: 'PUT',
        body: { priority }
      })
      toast('Priority updated')
      setPriorityOpen(false)
      load()
    } catch (e) {
      toast(e.message, 'error')
    }
  }

  async function handleAddComment(e) {
    e.preventDefault()
    if (!commentText.trim()) return
    setSubmitting(true)
    try {
      await api(`/bugs/${bugId}/comments`, {
        method: 'POST',
        body: { comment: commentText.trim() }
      })
      setCommentText('')
      toast('Comment added')
      load()
    } catch (err) {
      toast(err.message, 'error')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="space-y-6">
      {/* Top Breadcrumb & Navigation */}
      <div className="flex items-center justify-between text-xs text-slate-500">
        <a href="#/bugs" className="inline-flex items-center gap-1.5 hover:text-brand-600 transition font-medium">
          <Icon name="chevron" className="w-3.5 h-3.5 rotate-180" /> Back to Issue Registry
        </a>
        <div className="flex items-center gap-2">
          <span className="font-mono text-slate-400">ID: #{bug.id}</span>
          <span>·</span>
          <span>Reported {fmtRelative(bug.created_at)}</span>
        </div>
      </div>

      {/* Main 2-Column Grid (Jira / Linear style) */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 items-start">
        {/* Left Column (2 Cols): Core Details, Reproduction, Evidence, Fix, Comments & History */}
        <div className="lg:col-span-2 space-y-6">
          {/* Header Card */}
          <div className="card p-6 space-y-4">
            <div className="flex flex-wrap items-center gap-2">
              <span className="rounded bg-brand-50 dark:bg-brand-950/60 text-brand-700 dark:text-brand-300 px-2 py-0.5 text-xs font-mono font-bold border border-brand-200 dark:border-brand-800">
                #{bug.id}
              </span>
              <span className="rounded bg-slate-100 dark:bg-slate-800 px-2.5 py-0.5 text-xs font-semibold text-slate-700 dark:text-slate-300">
                {bug.module || 'Unspecified'}
              </span>
              <Badge value={bug.status} />
              <PriorityBadge value={bug.priority} />
            </div>

            <h1 className="text-xl md:text-2xl font-extrabold text-slate-900 dark:text-white leading-snug">
              {bug.title}
            </h1>

            {bug.description && (
              <div className="rounded-xl p-4 bg-slate-50 dark:bg-slate-800/40 border border-slate-100 dark:border-slate-800 text-sm text-slate-700 dark:text-slate-300 leading-relaxed whitespace-pre-wrap">
                {bug.description}
              </div>
            )}
          </div>

          {/* Environment Telemetry */}
          {(bug.operating_system || bug.browser_device || bug.app_version) && (
            <div className="card p-5 space-y-3">
              <h3 className="text-xs font-bold uppercase tracking-wider text-slate-400 flex items-center gap-2">
                <Icon name="laptop" className="w-4 h-4 text-brand-600" /> Environment Telemetry
              </h3>
              <div className="grid grid-cols-3 gap-3 text-xs">
                <div className="rounded-lg p-3 bg-slate-50 dark:bg-slate-800/50 border border-slate-100 dark:border-slate-800">
                  <div className="text-slate-400 mb-1">Operating System</div>
                  <div className="font-semibold text-slate-800 dark:text-slate-200">{bug.operating_system || '—'}</div>
                </div>
                <div className="rounded-lg p-3 bg-slate-50 dark:bg-slate-800/50 border border-slate-100 dark:border-slate-800">
                  <div className="text-slate-400 mb-1">Browser / Client</div>
                  <div className="font-semibold text-slate-800 dark:text-slate-200">{bug.browser_device || '—'}</div>
                </div>
                <div className="rounded-lg p-3 bg-slate-50 dark:bg-slate-800/50 border border-slate-100 dark:border-slate-800">
                  <div className="text-slate-400 mb-1">App Version</div>
                  <div className="font-semibold text-slate-800 dark:text-slate-200 font-mono">{bug.app_version || '—'}</div>
                </div>
              </div>
            </div>
          )}

          {/* Reproduction Details */}
          {(bug.steps_to_reproduce || bug.expected_result || bug.actual_result) && (
            <div className="card p-6 space-y-4">
              <h3 className="text-xs font-bold uppercase tracking-wider text-slate-400 flex items-center gap-2">
                <Icon name="code" className="w-4 h-4 text-brand-600" /> Reproduction Specifications
              </h3>

              {bug.steps_to_reproduce && (
                <div>
                  <div className="text-xs font-semibold text-slate-500 dark:text-slate-400 mb-1.5">Steps to Reproduce:</div>
                  <pre className="p-3.5 rounded-lg bg-slate-900 text-slate-200 font-mono text-xs overflow-x-auto whitespace-pre-wrap leading-relaxed">
                    {bug.steps_to_reproduce}
                  </pre>
                </div>
              )}

              <div className="grid md:grid-cols-2 gap-4 pt-1">
                {bug.expected_result && (
                  <div className="rounded-lg p-3.5 bg-emerald-50/50 dark:bg-emerald-950/20 border border-emerald-200/60 dark:border-emerald-900/40 text-xs">
                    <div className="font-bold text-emerald-800 dark:text-emerald-300 mb-1 flex items-center gap-1.5">
                      <Icon name="check-circle" className="w-4 h-4" /> Expected Outcome
                    </div>
                    <div className="text-slate-700 dark:text-slate-300 leading-relaxed">{bug.expected_result}</div>
                  </div>
                )}
                {bug.actual_result && (
                  <div className="rounded-lg p-3.5 bg-rose-50/50 dark:bg-rose-950/20 border border-rose-200/60 dark:border-rose-900/40 text-xs">
                    <div className="font-bold text-rose-800 dark:text-rose-300 mb-1 flex items-center gap-1.5">
                      <Icon name="x-circle" className="w-4 h-4" /> Actual Defect
                    </div>
                    <div className="text-slate-700 dark:text-slate-300 leading-relaxed">{bug.actual_result}</div>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* Developer Fix Description (if provided) */}
          {bug.fix_description && (
            <div className="card p-5 bg-emerald-50/40 dark:bg-emerald-950/20 border-emerald-200 dark:border-emerald-900/50 space-y-2">
              <h3 className="text-xs font-bold uppercase tracking-wider text-emerald-800 dark:text-emerald-400 flex items-center gap-2">
                <Icon name="check-circle" className="w-4 h-4" /> Developer Resolution &amp; Fix Notes
              </h3>
              <p className="text-xs text-slate-700 dark:text-slate-200 leading-relaxed whitespace-pre-wrap">
                {bug.fix_description}
              </p>
            </div>
          )}

          {/* Attachment Preview Card */}
          {bug.attachment_url && (
            <div className="card p-5 space-y-3">
              <div className="flex items-center justify-between">
                <h3 className="text-xs font-bold uppercase tracking-wider text-slate-400 flex items-center gap-2">
                  <Icon name="image" className="w-4 h-4 text-brand-600" /> Attached Evidence / Screenshot
                </h3>
                <button
                  type="button"
                  onClick={() => setLightboxOpen(true)}
                  className="text-xs text-brand-600 dark:text-brand-400 hover:underline font-semibold"
                >
                  View Fullscreen
                </button>
              </div>
              <div
                onClick={() => setLightboxOpen(true)}
                className="group relative cursor-pointer overflow-hidden rounded-xl border border-slate-200 dark:border-slate-800 max-h-72 bg-slate-900 flex items-center justify-center"
              >
                <img
                  src={apiAssetUrl(bug.attachment_url)}
                  alt="Bug attachment"
                  className="w-full object-contain max-h-72 transition duration-200 group-hover:scale-102"
                />
                <div className="absolute inset-0 bg-black/40 opacity-0 group-hover:opacity-100 transition flex items-center justify-center text-white text-xs font-semibold gap-1.5">
                  <Icon name="search" className="w-4 h-4" /> Click to Expand Image
                </div>
              </div>
            </div>
          )}

          {/* Tabs: Comments & Audit Trail */}
          <div className="card overflow-hidden">
            <div className="flex border-b border-slate-100 dark:border-slate-800 px-6 pt-2 bg-slate-50/50 dark:bg-slate-900/50">
              <button
                type="button"
                onClick={() => setActiveTab('comments')}
                className={`py-3 px-4 text-xs font-bold border-b-2 transition flex items-center gap-2 ${
                  activeTab === 'comments'
                    ? 'border-brand-600 text-brand-600 dark:text-brand-400'
                    : 'border-transparent text-slate-400 hover:text-slate-700 dark:hover:text-slate-200'
                }`}
              >
                <Icon name="comment" className="w-4 h-4" />
                Discussion &amp; Comments ({comments.length})
              </button>
              <button
                type="button"
                onClick={() => setActiveTab('history')}
                className={`py-3 px-4 text-xs font-bold border-b-2 transition flex items-center gap-2 ${
                  activeTab === 'history'
                    ? 'border-brand-600 text-brand-600 dark:text-brand-400'
                    : 'border-transparent text-slate-400 hover:text-slate-700 dark:hover:text-slate-200'
                }`}
              >
                <Icon name="timeline" className="w-4 h-4" />
                Audit Trail &amp; History ({history.length})
              </button>
            </div>

            <div className="p-6">
              {activeTab === 'comments' ? (
                <div className="space-y-6">
                  {/* Comments list */}
                  {comments.length === 0 ? (
                    <div className="text-center py-8 text-xs text-slate-400">
                      No comments yet. Start the conversation below.
                    </div>
                  ) : (
                    <div className="space-y-4">
                      {comments.map((c) => (
                        <div key={c.id} className="flex items-start gap-3.5">
                          <div className="w-8 h-8 rounded-full bg-brand-500/15 text-brand-600 dark:text-brand-300 font-bold text-xs flex items-center justify-center shrink-0 border border-brand-500/20">
                            {(c.user_name || 'U')[0]}
                          </div>
                          <div className="min-w-0 flex-1 rounded-xl p-3.5 bg-slate-50 dark:bg-slate-800/70 border border-slate-100 dark:border-slate-800 text-xs">
                            <div className="flex items-center justify-between gap-2 mb-1">
                              <div className="flex items-center gap-2">
                                <span className="font-bold text-slate-900 dark:text-white">{c.user_name}</span>
                                {c.user_role && (
                                  <span className="rounded px-1.5 py-0.2 capitalize text-[10px] font-semibold bg-slate-200 dark:bg-slate-700 text-slate-600 dark:text-slate-300">
                                    {c.user_role}
                                  </span>
                                )}
                              </div>
                              <span className="text-[11px] text-slate-400">{fmtRelative(c.created_at)}</span>
                            </div>
                            <p className="text-slate-700 dark:text-slate-300 leading-relaxed whitespace-pre-wrap">{c.comment}</p>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}

                  {/* Add comment box */}
                  <form onSubmit={handleAddComment} className="pt-2">
                    <label className="label">Add to conversation</label>
                    <textarea
                      className="input min-h-[85px] mb-2"
                      value={commentText}
                      onChange={(e) => setCommentText(e.target.value)}
                      placeholder="Share progress, reproduction feedback, or testing verification..."
                    />
                    <div className="flex justify-end">
                      <button className="btn-primary text-xs" disabled={submitting || !commentText.trim()}>
                        {submitting ? 'Posting…' : 'Post Comment'}
                      </button>
                    </div>
                  </form>
                </div>
              ) : (
                /* History Timeline */
                <div className="relative pl-6 space-y-6 before:absolute before:left-2.5 before:top-2 before:bottom-2 before:w-0.5 before:bg-slate-200 dark:before:bg-slate-800">
                  {history.map((h) => (
                    <div key={h.id} className="relative">
                      <div className="absolute -left-6 top-0.5 w-5 h-5 rounded-full bg-white dark:bg-slate-900 border-2 border-brand-500 flex items-center justify-center text-[10px]">
                        <Icon name={HISTORY_ICONS[h.action] || 'refresh'} className="w-2.5 h-2.5 text-brand-600" />
                      </div>
                      <div className="text-xs">
                        <div className="flex items-center gap-2">
                          <span className="font-bold text-slate-900 dark:text-white">{h.user_name || 'System'}</span>
                          <span className="text-slate-400">·</span>
                          <span className="text-slate-400">{fmt(h.timestamp)}</span>
                        </div>
                        <div className="text-slate-600 dark:text-slate-300 mt-1">
                          {h.note || (
                            <span>
                              Changed <span className="font-mono text-slate-500">{h.action}</span>
                              {h.old_value && <> from <b>{h.old_value}</b></>}
                              {h.new_value && <> to <b>{h.new_value}</b></>}
                            </span>
                          )}
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Right Column (1 Col): Lifecycle Actions, Assignee, Priority & Severity */}
        <div className="space-y-5">
          {/* Workflow & Lifecycle State Actions */}
          <div className="card p-5 space-y-4 shadow-sm border-brand-200/50 dark:border-brand-900/30">
            <h3 className="text-xs font-bold uppercase tracking-wider text-slate-400 flex items-center justify-between">
              <span>Status Workflow</span>
              <span className="text-[10px] text-slate-400 font-mono">Role: {user.role}</span>
            </h3>

            <div className="rounded-xl p-3.5 bg-slate-50 dark:bg-slate-800/60 border border-slate-100 dark:border-slate-800 flex items-center justify-between">
              <div>
                <div className="text-[11px] text-slate-400">Current Lifecycle State</div>
                <div className="font-bold text-slate-900 dark:text-white mt-0.5">{bug.status_label || bug.status}</div>
              </div>
              <Badge value={bug.status} />
            </div>

            {/* Next Allowed Transitions for Current User */}
            <div>
              <div className="text-xs font-semibold text-slate-600 dark:text-slate-400 mb-2">Available Actions:</div>
              {bug.allowed_next && bug.allowed_next.length > 0 ? (
                <div className="space-y-2">
                  {bug.allowed_next.map((nxt) => (
                    <button
                      key={nxt}
                      type="button"
                      onClick={() => handleActionClick(nxt)}
                      className={`btn w-full justify-center text-xs py-2 font-bold shadow-xs ${
                        ACTION_COLORS[nxt] || 'btn-secondary'
                      }`}
                    >
                      {ACTION_LABELS[nxt] || `Move to ${nxt}`}
                    </button>
                  ))}
                </div>
              ) : (
                <div className="text-xs text-slate-400 italic p-2 rounded bg-slate-50 dark:bg-slate-800/40 border border-dashed border-slate-200 dark:border-slate-800">
                  No workflow transitions currently permitted for role '{user.role}' in this state.
                </div>
              )}
            </div>
          </div>

          {/* People & Assignment Card */}
          <div className="card p-5 space-y-3">
            <div className="flex items-center justify-between">
              <h3 className="text-xs font-bold uppercase tracking-wider text-slate-400">Assignee</h3>
              {isAdmin && (
                <button
                  type="button"
                  onClick={() => setAssignOpen(true)}
                  className="text-xs text-brand-600 dark:text-brand-400 hover:underline font-semibold"
                >
                  Change
                </button>
              )}
            </div>

            <div className="flex items-center gap-3 p-3 rounded-xl bg-slate-50 dark:bg-slate-800/50 border border-slate-100 dark:border-slate-800">
              <div className="w-10 h-10 rounded-full bg-blue-100 dark:bg-blue-950 text-blue-700 dark:text-blue-300 font-bold flex items-center justify-center shrink-0">
                {bug.assigned_name ? bug.assigned_name[0] : '?'}
              </div>
              <div className="min-w-0">
                <div className="font-bold text-xs text-slate-900 dark:text-white truncate">
                  {bug.assigned_name || 'Unassigned'}
                </div>
                <div className="text-[11px] text-slate-400">Assigned Developer</div>
              </div>
            </div>

            <div className="pt-2 border-t border-slate-100 dark:border-slate-800">
              <div className="text-[11px] text-slate-400">Reporter:</div>
              <div className="font-semibold text-xs text-slate-800 dark:text-slate-200 mt-0.5">
                {bug.creator_name || 'Unknown Reporter'}
              </div>
            </div>
          </div>

          {/* Severity & Priority Meta */}
          <div className="card p-5 space-y-3.5">
            <div className="flex items-center justify-between">
              <h3 className="text-xs font-bold uppercase tracking-wider text-slate-400">Defect Metadata</h3>
              {isAdmin && (
                <button
                  type="button"
                  onClick={() => setPriorityOpen(true)}
                  className="text-xs text-brand-600 dark:text-brand-400 hover:underline font-semibold"
                >
                  Override Priority
                </button>
              )}
            </div>

            <div className="grid grid-cols-2 gap-2.5 text-xs">
              <div className="rounded-lg p-3 bg-slate-50 dark:bg-slate-800/50 border border-slate-100 dark:border-slate-800">
                <div className="text-slate-400 mb-1">Severity</div>
                <Badge value={bug.severity} kind="severity" />
              </div>
              <div className="rounded-lg p-3 bg-slate-50 dark:bg-slate-800/50 border border-slate-100 dark:border-slate-800">
                <div className="text-slate-400 mb-1">Effective Priority</div>
                <PriorityBadge value={bug.priority} />
              </div>
            </div>

            <div className="rounded-lg p-3 bg-brand-50/50 dark:bg-brand-950/20 border border-brand-100 dark:border-brand-900/40 text-xs">
              <div className="text-slate-400 mb-0.5">Recommended Priority</div>
              <div className="font-semibold text-slate-800 dark:text-slate-200">
                {bug.recommended_priority || bug.priority}
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Lightbox Modal for Attachment */}
      <Modal open={lightboxOpen} onClose={() => setLightboxOpen(false)} title="Screenshot Preview" wide>
        <div className="flex flex-col items-center">
          <img src={apiAssetUrl(bug.attachment_url)} alt="Fullscreen Attachment" className="max-h-[75vh] object-contain rounded-lg shadow-xl" />
          <a
            href={apiAssetUrl(bug.attachment_url)}
            target="_blank"
            rel="noopener noreferrer"
            className="btn-secondary mt-4 text-xs"
          >
            Open Original File In New Tab
          </a>
        </div>
      </Modal>

      {/* Action Transition Modal (Fix Description / Reopen Reason / Note) */}
      <Modal
        open={actionModalOpen}
        onClose={() => setActionModalOpen(false)}
        title={targetStatus ? ACTION_LABELS[targetStatus] || `Confirm ${targetStatus}` : 'Transition Bug'}
      >
        <div className="space-y-4">
          {targetStatus === 'fixed' && (
            <div>
              <label className="label">Describe Your Fix (required for developers) *</label>
              <textarea
                className="input min-h-[90px]"
                required
                value={fixDescription}
                onChange={(e) => setFixDescription(e.target.value)}
                placeholder="Explain what code changes were committed, PR links, and how the issue was resolved..."
              />
            </div>
          )}

          {targetStatus === 'reopened' && (
            <div>
              <label className="label">Reason for Reopening (Tester Feedback) *</label>
              <textarea
                className="input min-h-[90px]"
                required
                value={statusNote}
                onChange={(e) => setStatusNote(e.target.value)}
                placeholder="Explain why verification failed and steps observed..."
              />
            </div>
          )}

          {targetStatus !== 'fixed' && targetStatus !== 'reopened' && (
            <div>
              <label className="label">Transition Note (optional)</label>
              <textarea
                className="input min-h-[70px]"
                value={statusNote}
                onChange={(e) => setStatusNote(e.target.value)}
                placeholder="Optional explanation for audit log..."
              />
            </div>
          )}

          <div className="flex justify-end gap-2 pt-2">
            <button type="button" onClick={() => setActionModalOpen(false)} className="btn-secondary">
              Cancel
            </button>
            <button
              type="button"
              onClick={() => executeStatusChange(targetStatus, statusNote, fixDescription)}
              disabled={submitting || (targetStatus === 'fixed' && !fixDescription.trim()) || (targetStatus === 'reopened' && !statusNote.trim())}
              className={`btn font-bold text-xs ${ACTION_COLORS[targetStatus] || 'btn-primary'}`}
            >
              {submitting ? 'Applying…' : 'Confirm Transition'}
            </button>
          </div>
        </div>
      </Modal>

      {/* Admin Assign Developer Modal */}
      <Modal open={assignOpen} onClose={() => setAssignOpen(false)} title="Assign Bug to Developer">
        <div className="space-y-4">
          <p className="text-xs text-slate-500">Select an engineer from the registered developers list:</p>
          <div className="space-y-2 max-h-60 overflow-y-auto">
            <button
              type="button"
              onClick={() => handleAssign(null)}
              className="w-full text-left p-2.5 rounded-lg border border-slate-200 dark:border-slate-700 hover:bg-slate-50 dark:hover:bg-slate-800 text-xs font-medium text-slate-500"
            >
              — Unassign Issue —
            </button>
            {developers.map((d) => (
              <button
                key={d.id}
                type="button"
                onClick={() => handleAssign(d.id)}
                className={`w-full text-left p-3 rounded-lg border transition text-xs flex items-center justify-between ${
                  bug.assigned_to === d.id
                    ? 'border-brand-500 bg-brand-50 dark:bg-brand-950/40 text-brand-700 dark:text-brand-300 font-bold'
                    : 'border-slate-200 dark:border-slate-700 hover:bg-slate-50 dark:hover:bg-slate-800 text-slate-800 dark:text-slate-200'
                }`}
              >
                <div>
                  <div className="font-semibold">{d.name}</div>
                  <div className="text-[11px] text-slate-400">{d.email}</div>
                </div>
                {bug.assigned_to === d.id && <Icon name="check" className="w-4 h-4 text-brand-600" />}
              </button>
            ))}
          </div>
        </div>
      </Modal>

      {/* Admin Override Priority Modal */}
      <Modal open={priorityOpen} onClose={() => setPriorityOpen(false)} title="Admin Priority Override">
        <div className="space-y-4">
          <p className="text-xs text-slate-500">
            System recommended priority is <b>{bug.recommended_priority || 'Medium'}</b>. Choose an override value:
          </p>
          <div className="grid grid-cols-2 gap-2">
            {['Critical', 'High', 'Medium', 'Low'].map((p) => (
              <button
                key={p}
                type="button"
                onClick={() => handleOverridePriority(p)}
                className={`p-3 rounded-lg border text-xs font-bold transition ${
                  bug.priority === p
                    ? 'border-brand-600 bg-brand-50 dark:bg-brand-950/50 text-brand-700 dark:text-brand-300 shadow-xs'
                    : 'border-slate-200 dark:border-slate-700 hover:bg-slate-50 dark:hover:bg-slate-800 text-slate-800 dark:text-slate-200'
                }`}
              >
                {p}
              </button>
            ))}
          </div>
        </div>
      </Modal>
    </div>
  )
}
