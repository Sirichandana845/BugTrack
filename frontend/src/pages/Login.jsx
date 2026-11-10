import { useState } from 'react'
import { api, registerUser, forgotPassword, resetPassword, setToken, toast } from '../services/api'
import Icon from '../components/Icon'
import { Modal } from '../components/ui'

const DEMO = [
  { label: 'Admin', role: 'admin', email: 'admin@bugtrack.dev', password: 'admin123' },
  { label: 'Developer', role: 'developer', email: 'dev@bugtrack.dev', password: 'dev123' },
  { label: 'Tester', role: 'tester', email: 'tester@bugtrack.dev', password: 'tester123' },
  { label: 'Reporter', role: 'reporter', email: 'reporter@bugtrack.dev', password: 'reporter123' }
]

export default function Login({ onLogin }) {
  const [mode, setMode] = useState('login') // 'login' | 'register'
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [name, setName] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  // Forgot password modal state
  const [forgotOpen, setForgotOpen] = useState(false)
  const [forgotEmail, setForgotEmail] = useState('')
  const [resetToken, setResetToken] = useState('')
  const [newPassword, setNewPassword] = useState('')
  const [forgotStep, setForgotStep] = useState(1) // 1: request, 2: reset
  const [forgotMsg, setForgotMsg] = useState('')

  async function handleLogin(e) {
    e.preventDefault()
    setError('')
    setBusy(true)
    try {
      const data = await api('/login', { method: 'POST', body: { email, password } })
      setToken(data.token)
      localStorage.setItem('bt_user', JSON.stringify(data.user))
      toast(`Welcome back, ${data.user.name}!`)
      onLogin(data.user)
      window.location.hash = '#/'
    } catch (err) {
      setError(err.message)
    } finally {
      setBusy(false)
    }
  }

  async function handleRegister(e) {
    e.preventDefault()
    setError('')
    if (password !== confirmPassword) {
      setError('Passwords do not match.')
      return
    }
    if (password.length < 6) {
      setError('Password must be at least 6 characters.')
      return
    }
    setBusy(true)
    try {
      const data = await registerUser({ name, email, password })
      setToken(data.token)
      localStorage.setItem('bt_user', JSON.stringify(data.user))
      toast(`Account created! Welcome, ${data.user.name}!`)
      onLogin(data.user)
      window.location.hash = '#/'
    } catch (err) {
      setError(err.message)
    } finally {
      setBusy(false)
    }
  }

  async function handleForgotPassword(e) {
    e.preventDefault()
    setBusy(true)
    setError('')
    try {
      const data = await forgotPassword(forgotEmail)
      setForgotMsg(data.message)
      if (data.reset_token) {
        setResetToken(data.reset_token)
        setForgotStep(2)
      } else {
        toast('Reset instructions sent.')
      }
    } catch (err) {
      setError(err.message)
    } finally {
      setBusy(false)
    }
  }

  async function handleResetPassword(e) {
    e.preventDefault()
    setBusy(true)
    setError('')
    try {
      await resetPassword({ token: resetToken, password: newPassword })
      toast('Password reset successfully! You can now log in.')
      setForgotOpen(false)
      setForgotStep(1)
      setPassword(newPassword)
      setEmail(forgotEmail)
    } catch (err) {
      setError(err.message)
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-radial from-slate-900 via-slate-950 to-black p-4">
      <div className="w-full max-w-md">
        {/* Brand Header */}
        <div className="flex flex-col items-center text-center mb-6">
          <div className="inline-flex items-center justify-center w-14 h-14 rounded-2xl bg-brand-600 text-white shadow-xl shadow-brand-500/20 mb-3">
            <Icon name="bug" className="w-8 h-8" />
          </div>
          <h1 className="text-3xl font-extrabold text-white tracking-tight">BugTrack</h1>
          <p className="text-sm text-slate-400 mt-1">
            Enterprise Bug Tracking, Prioritization &amp; Quality System
          </p>
        </div>

        {/* Auth Card */}
        <div className="card p-7 shadow-2xl bg-white dark:bg-slate-900 border-slate-200 dark:border-slate-800">
          {/* Tabs */}
          <div className="flex rounded-lg bg-slate-100 dark:bg-slate-800 p-1 mb-6">
            <button
              type="button"
              onClick={() => { setMode('login'); setError('') }}
              className={`flex-1 py-2 text-xs font-bold rounded-md transition ${
                mode === 'login'
                  ? 'bg-white dark:bg-slate-900 text-slate-900 dark:text-white shadow-xs'
                  : 'text-slate-500 hover:text-slate-800 dark:hover:text-slate-200'
              }`}
            >
              Sign In
            </button>
            <button
              type="button"
              onClick={() => { setMode('register'); setError('') }}
              className={`flex-1 py-2 text-xs font-bold rounded-md transition ${
                mode === 'register'
                  ? 'bg-white dark:bg-slate-900 text-slate-900 dark:text-white shadow-xs'
                  : 'text-slate-500 hover:text-slate-800 dark:hover:text-slate-200'
              }`}
            >
              Register (Reporter)
            </button>
          </div>

          {mode === 'login' ? (
            /* Login Form */
            <form onSubmit={handleLogin} className="space-y-4">
              <div>
                <label className="label">Work Email</label>
                <div className="relative">
                  <input
                    className="input pr-9"
                    type="email"
                    required
                    value={email}
                    placeholder="name@company.com"
                    onChange={(e) => setEmail(e.target.value)}
                  />
                  <div className="absolute right-3 top-2.5 text-slate-400">
                    <Icon name="user" className="w-4 h-4" />
                  </div>
                </div>
              </div>

              <div>
                <div className="flex items-center justify-between mb-1">
                  <label className="label mb-0">Password</label>
                  <button
                    type="button"
                    onClick={() => { setForgotOpen(true); setForgotEmail(email); setError('') }}
                    className="text-xs text-brand-600 dark:text-brand-400 hover:underline"
                  >
                    Forgot password?
                  </button>
                </div>
                <div className="relative">
                  <input
                    className="input pr-10"
                    type={showPassword ? 'text' : 'password'}
                    required
                    value={password}
                    placeholder="••••••••"
                    onChange={(e) => setPassword(e.target.value)}
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword(!showPassword)}
                    className="absolute right-3 top-2.5 text-slate-400 hover:text-slate-600 dark:hover:text-slate-200"
                    title={showPassword ? 'Hide password' : 'Show password'}
                  >
                    <Icon name={showPassword ? 'eye-off' : 'eye'} className="w-4 h-4" />
                  </button>
                </div>
              </div>

              {error && (
                <div className="rounded-lg bg-rose-50 dark:bg-rose-950/40 border border-rose-200 dark:border-rose-900 text-rose-700 dark:text-rose-300 text-xs px-3.5 py-2.5 flex items-center gap-2">
                  <Icon name="alert" className="w-4 h-4 shrink-0" />
                  <span>{error}</span>
                </div>
              )}

              <button className="btn-primary w-full justify-center py-2.5 text-sm" disabled={busy}>
                {busy ? 'Signing in…' : 'Sign In'}
              </button>
            </form>
          ) : (
            /* Public Registration Form */
            <form onSubmit={handleRegister} className="space-y-4">
              <div className="rounded-lg bg-amber-50 dark:bg-amber-950/30 border border-amber-200 dark:border-amber-900/60 p-3 text-xs text-amber-800 dark:text-amber-300 flex items-start gap-2.5">
                <Icon name="shield" className="w-4 h-4 shrink-0 mt-0.5" />
                <div>
                  <b>Public Access:</b> New registrations are automatically granted the <b>Reporter</b> role to report problems, attach screenshots, and follow resolution status.
                </div>
              </div>

              <div>
                <label className="label">Full Name *</label>
                <input
                  className="input"
                  type="text"
                  required
                  value={name}
                  placeholder="e.g. John Doe"
                  onChange={(e) => setName(e.target.value)}
                />
              </div>

              <div>
                <label className="label">Email Address *</label>
                <input
                  className="input"
                  type="email"
                  required
                  value={email}
                  placeholder="john@example.com"
                  onChange={(e) => setEmail(e.target.value)}
                />
              </div>

              <div>
                <label className="label">Password (min 6 characters) *</label>
                <div className="relative">
                  <input
                    className="input pr-10"
                    type={showPassword ? 'text' : 'password'}
                    required
                    value={password}
                    placeholder="••••••••"
                    onChange={(e) => setPassword(e.target.value)}
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword(!showPassword)}
                    className="absolute right-3 top-2.5 text-slate-400 hover:text-slate-600 dark:hover:text-slate-200"
                  >
                    <Icon name={showPassword ? 'eye-off' : 'eye'} className="w-4 h-4" />
                  </button>
                </div>
              </div>

              <div>
                <label className="label">Confirm Password *</label>
                <input
                  className="input"
                  type={showPassword ? 'text' : 'password'}
                  required
                  value={confirmPassword}
                  placeholder="••••••••"
                  onChange={(e) => setConfirmPassword(e.target.value)}
                />
              </div>

              {error && (
                <div className="rounded-lg bg-rose-50 dark:bg-rose-950/40 border border-rose-200 dark:border-rose-900 text-rose-700 dark:text-rose-300 text-xs px-3.5 py-2.5 flex items-center gap-2">
                  <Icon name="alert" className="w-4 h-4 shrink-0" />
                  <span>{error}</span>
                </div>
              )}

              <button className="btn-primary w-full justify-center py-2.5 text-sm" disabled={busy}>
                {busy ? 'Creating Account…' : 'Complete Registration'}
              </button>
            </form>
          )}

          {/* Demo Accounts Quick-Fill */}
          <div className="mt-6 pt-5 border-t border-slate-100 dark:border-slate-800">
            <div className="flex items-center justify-between mb-2.5">
              <span className="text-[11px] font-bold uppercase tracking-wider text-slate-400">
                Demo Accounts — 1-Click Fill
              </span>
              <span className="text-[10px] text-brand-600 dark:text-brand-400">All 4 Roles</span>
            </div>
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
              {DEMO.map((d) => (
                <button
                  key={d.label}
                  type="button"
                  onClick={() => {
                    setMode('login')
                    setEmail(d.email)
                    setPassword(d.password)
                    setError('')
                  }}
                  className="rounded-lg border border-slate-200 dark:border-slate-700 px-2.5 py-2 text-left hover:border-brand-500 hover:bg-brand-50/50 dark:hover:bg-slate-800 transition group"
                >
                  <div className="text-xs font-bold text-slate-800 dark:text-slate-200 group-hover:text-brand-600 dark:group-hover:text-brand-400">
                    {d.label}
                  </div>
                  <div className="text-[10px] text-slate-400 truncate capitalize">{d.role}</div>
                </button>
              ))}
            </div>
          </div>
        </div>

        {/* Forgot Password Modal */}
        <Modal open={forgotOpen} onClose={() => setForgotOpen(false)} title="Reset Password">
          {forgotStep === 1 ? (
            <form onSubmit={handleForgotPassword} className="space-y-4">
              <p className="text-sm text-slate-600 dark:text-slate-300">
                Enter your account email to receive or generate a password reset token.
              </p>
              <div>
                <label className="label">Account Email</label>
                <input
                  className="input"
                  type="email"
                  required
                  value={forgotEmail}
                  onChange={(e) => setForgotEmail(e.target.value)}
                  placeholder="admin@bugtrack.dev"
                />
              </div>
              {error && <div className="text-xs text-rose-600">{error}</div>}
              <div className="flex justify-end gap-2 pt-2">
                <button type="button" onClick={() => setForgotOpen(false)} className="btn-secondary">
                  Cancel
                </button>
                <button className="btn-primary" disabled={busy}>
                  {busy ? 'Processing…' : 'Generate Token'}
                </button>
              </div>
            </form>
          ) : (
            <form onSubmit={handleResetPassword} className="space-y-4">
              <div className="rounded-lg bg-emerald-50 dark:bg-emerald-950/40 p-3 text-xs text-emerald-800 dark:text-emerald-300">
                {forgotMsg || 'Reset token generated successfully.'}
              </div>
              <div>
                <label className="label">Reset Token</label>
                <input
                  className="input font-mono text-xs"
                  required
                  value={resetToken}
                  onChange={(e) => setResetToken(e.target.value)}
                />
              </div>
              <div>
                <label className="label">New Password (min 6 chars)</label>
                <input
                  className="input"
                  type="password"
                  required
                  value={newPassword}
                  placeholder="••••••••"
                  onChange={(e) => setNewPassword(e.target.value)}
                />
              </div>
              {error && <div className="text-xs text-rose-600">{error}</div>}
              <div className="flex justify-end gap-2 pt-2">
                <button type="button" onClick={() => setForgotOpen(false)} className="btn-secondary">
                  Cancel
                </button>
                <button className="btn-primary" disabled={busy}>
                  {busy ? 'Updating…' : 'Set New Password'}
                </button>
              </div>
            </form>
          )}
        </Modal>

        {/* Footer info */}
        <p className="text-center text-xs text-slate-500 mt-6">
          BugTrack Engineering Platform · Secure JWT Authentication &amp; RBAC
        </p>
      </div>
    </div>
  )
}
