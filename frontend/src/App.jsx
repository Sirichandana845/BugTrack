// App shell: Jira/Linear aesthetic + real-time notification polling + light/dark theme + RBAC
import { createContext, useContext, useEffect, useState, useRef } from 'react'
import {
  api, getToken, setToken, setToastHandler,
  fetchNotifications, markNotificationRead, markAllNotificationsRead,
  updateProfile, fmtRelative
} from './services/api'
import Icon from './components/Icon'
import { Modal } from './components/ui'
import Login from './pages/Login'
import Dashboard from './pages/Dashboard'
import BugList from './pages/BugList'
import ReportBug from './pages/ReportBug'
import BugDetails from './pages/BugDetails'
import Developers from './pages/Developers'
import Users from './pages/Users'
import Reports from './pages/Reports'
import ImportData from './pages/ImportData'

export const AuthCtx = createContext(null)
export const useAuth = () => useContext(AuthCtx)

function parseHash() {
  return window.location.hash.replace(/^#\/?/, '').split('/').filter(Boolean)
}

const TITLES = {
  dashboard: 'Dashboard',
  bugs: 'Issue Registry',
  report: 'Report Defect',
  developers: 'Developer Directory',
  users: 'User & Role Management',
  reports: 'Analytics & Reports',
  import: 'Kaggle Dataset Import',
  'my-bugs': 'My Assigned Tasks',
  'my-reports': 'My Reported Issues'
}

export default function App() {
  const [user, setUser] = useState(null)
  const [loading, setLoading] = useState(true)
  const [route, setRoute] = useState(parseHash())
  const [toasts, setToasts] = useState([])
  const [darkMode, setDarkMode] = useState(() => localStorage.getItem('bt_theme') === 'dark')

  // Notification state
  const [notifications, setNotifications] = useState([])
  const [unreadCount, setUnreadCount] = useState(0)

  // Profile modal state
  const [profileOpen, setProfileOpen] = useState(false)

  // Sync dark mode class with root html element
  useEffect(() => {
    if (darkMode) {
      document.documentElement.classList.add('dark')
      localStorage.setItem('bt_theme', 'dark')
    } else {
      document.documentElement.classList.remove('dark')
      localStorage.setItem('bt_theme', 'light')
    }
  }, [darkMode])

  useEffect(() => {
    const onHash = () => setRoute(parseHash())
    window.addEventListener('hashchange', onHash)
    return () => window.removeEventListener('hashchange', onHash)
  }, [])

  // Load current user
  useEffect(() => {
    if (getToken()) {
      api('/me')
        .then((d) => setUser(d.user))
        .catch(() => { setToken(''); setUser(null) })
        .finally(() => setLoading(false))
    } else setLoading(false)
  }, [])

  // Setup toast handler
  useEffect(() => {
    setToastHandler((msg, type) => {
      const id = Date.now() + Math.random()
      setToasts((t) => [...t, { id, msg, type }])
      setTimeout(() => setToasts((t) => t.filter((x) => x.id !== id)), 3800)
    })
  }, [])

  // Real-time automatic notification polling (every 8 seconds)
  useEffect(() => {
    if (!user) return
    const poll = () => {
      fetchNotifications()
        .then((res) => {
          setNotifications(res.notifications || [])
          setUnreadCount(res.unread_count || 0)
        })
        .catch(() => {})
    }
    poll()
    const timer = setInterval(poll, 8000)
    return () => clearInterval(timer)
  }, [user])

  const logout = () => {
    setToken('')
    localStorage.removeItem('bt_user')
    setUser(null)
    window.location.hash = '#/'
  }

  if (loading) {
    return (
      <div className="h-screen flex flex-col items-center justify-center bg-slate-900 text-slate-300 gap-3">
        <div className="w-9 h-9 border-3 border-brand-500 border-t-transparent rounded-full animate-spin" />
        <span className="text-sm font-semibold tracking-wide">Starting BugTrack Platform…</span>
      </div>
    )
  }

  if (!user) return <Login onLogin={setUser} />

  const [seg, id] = route
  let page
  switch (seg) {
    case 'dashboard': page = <Dashboard />; break
    case 'bugs': page = id ? <BugDetails key={id} bugId={Number(id)} /> : <BugList />; break
    case 'my-bugs': page = <BugList assignedMe />; break
    case 'my-reports': page = <BugList reportedMe />; break
    case 'report': page = <ReportBug />; break
    case 'developers': page = <Developers />; break
    case 'users': page = <Users />; break
    case 'reports': page = <Reports />; break
    case 'import': page = <ImportData />; break
    default: page = <Dashboard />
  }

  const title = id ? `Defect #${id}` : (TITLES[seg] || 'BugTrack')

  return (
    <AuthCtx.Provider value={{ user, setUser, logout, darkMode, setDarkMode }}>
      <div className="min-h-screen flex bg-slate-50 dark:bg-slate-950 text-slate-800 dark:text-slate-100 transition-colors duration-150">
        <Sidebar current={seg} />
        <div className="flex-1 flex flex-col min-w-0">
          <Topbar
            title={title}
            notifications={notifications}
            unreadCount={unreadCount}
            onOpenProfile={() => setProfileOpen(true)}
            onNotificationRead={async (notifId) => {
              await markNotificationRead(notifId)
              setNotifications((prev) => prev.map((n) => n.id === notifId ? { ...n, is_read: 1 } : n))
              setUnreadCount((c) => Math.max(0, c - 1))
            }}
            onMarkAllRead={async () => {
              await markAllNotificationsRead()
              setNotifications((prev) => prev.map((n) => ({ ...n, is_read: 1 })))
              setUnreadCount(0)
            }}
          />
          <main className="flex-1 p-5 md:p-8 max-w-7xl w-full mx-auto">{page}</main>
        </div>
      </div>

      {/* User Profile Modal */}
      <ProfileModal
        open={profileOpen}
        onClose={() => setProfileOpen(false)}
        user={user}
        onUserUpdated={setUser}
      />

      {/* System Toasts */}
      <div className="fixed bottom-5 right-5 z-60 space-y-2 pointer-events-none">
        {toasts.map((t) => (
          <div
            key={t.id}
            className={`flex items-center gap-2.5 rounded-xl px-4 py-3 text-xs font-bold shadow-2xl text-white pointer-events-auto animate-fadeIn ${
              t.type === 'error' ? 'bg-rose-600' : 'bg-slate-900 border border-slate-700'
            }`}
          >
            <Icon name={t.type === 'error' ? 'alert' : 'check-circle'} className="w-4 h-4 shrink-0" />
            <span>{t.msg}</span>
          </div>
        ))}
      </div>
    </AuthCtx.Provider>
  )
}

function Sidebar({ current }) {
  const { user, logout } = useAuth()
  const [collapsed, setCollapsed] = useState(false)

  const items = [
    { key: 'dashboard', label: 'Dashboard', icon: 'dashboard' },
    ...(user.role === 'developer'
      ? [{ key: 'my-bugs', label: 'My Assigned Tasks', icon: 'flag' }]
      : []),
    ...(user.role === 'reporter'
      ? [{ key: 'my-reports', label: 'My Reported Issues', icon: 'timeline' }]
      : []),
    { key: 'bugs', label: 'All Issues', icon: 'list' },
    { key: 'report', label: 'Report Defect', icon: 'plus' },
    ...(user.role !== 'reporter'
      ? [{ key: 'developers', label: 'Developers', icon: 'users' }]
      : []),
    ...(user.role === 'admin' ? [
      { key: 'reports', label: 'Reports & Export', icon: 'chart' },
      { key: 'users', label: 'User Management', icon: 'gear' },
      { key: 'import', label: 'Dataset Import', icon: 'box' },
    ] : [])
  ]

  const roleColors = {
    admin: 'bg-indigo-500/15 text-indigo-400 border-indigo-500/30',
    developer: 'bg-blue-500/15 text-blue-400 border-blue-500/30',
    tester: 'bg-emerald-500/15 text-emerald-400 border-emerald-500/30',
    reporter: 'bg-amber-500/15 text-amber-400 border-amber-500/30'
  }

  return (
    <aside
      className={`shrink-0 bg-slate-950 text-slate-300 flex flex-col sticky top-0 h-screen border-r border-slate-900 transition-all duration-200 z-30 ${
        collapsed ? 'w-18' : 'w-64'
      }`}
    >
      {/* Brand Header */}
      <div className="flex items-center justify-between px-4 py-4.5 border-b border-slate-900">
        <a href="#/" className="flex items-center gap-3 min-w-0">
          <span className="inline-flex items-center justify-center w-9 h-9 rounded-xl bg-brand-600 text-white shadow-md shadow-brand-500/20 shrink-0">
            <Icon name="bug" className="w-5 h-5" />
          </span>
          {!collapsed && (
            <div className="min-w-0">
              <div className="font-extrabold text-white text-base tracking-tight leading-none">BugTrack</div>
              <div className="text-[10px] text-slate-400 mt-1 uppercase tracking-wider font-semibold">
                SaaS Quality Platform
              </div>
            </div>
          )}
        </a>
        <button
          onClick={() => setCollapsed(!collapsed)}
          className="text-slate-500 hover:text-white p-1 rounded-md hidden md:block"
          title={collapsed ? "Expand sidebar" : "Collapse sidebar"}
        >
          <Icon name="chevron" className={`w-4 h-4 transition ${collapsed ? '' : 'rotate-180'}`} />
        </button>
      </div>

      {/* Navigation Links */}
      <nav className="flex-1 px-3 py-4 space-y-1 overflow-y-auto">
        {items.map((item) => {
          const active = current === item.key || (item.key === 'bugs' && current === 'bugs')
          return (
            <a
              key={item.key}
              href={'#/' + item.key}
              title={collapsed ? item.label : undefined}
              className={`flex items-center gap-3 rounded-xl px-3 py-2.5 text-xs font-bold transition ${
                active
                  ? 'bg-brand-600 text-white shadow-md shadow-brand-600/30'
                  : 'text-slate-400 hover:bg-slate-900 hover:text-white'
              }`}
            >
              <Icon name={item.icon} className="w-4 h-4 shrink-0" />
              {!collapsed && <span className="truncate">{item.label}</span>}
            </a>
          )
        })}
      </nav>

      {/* User Footer Profile */}
      <div className="p-3 border-t border-slate-900">
        <div className={`flex items-center gap-3 rounded-xl p-2.5 bg-slate-900/60 border border-slate-800/80 ${collapsed ? 'justify-center' : ''}`}>
          <div className="w-8 h-8 rounded-full bg-brand-600 flex items-center justify-center text-white text-xs font-bold shrink-0">
            {user.name.split(' ').map((n) => n[0]).join('').slice(0, 2)}
          </div>
          {!collapsed && (
            <div className="min-w-0 flex-1">
              <div className="text-xs font-bold text-white truncate">{user.name}</div>
              <div className={`inline-block text-[10px] uppercase font-bold tracking-wider rounded px-1.5 py-0.2 border mt-0.5 ${roleColors[user.role] || ''}`}>
                {user.role}
              </div>
            </div>
          )}
          {!collapsed && (
            <button onClick={logout} title="Log out" className="text-slate-400 hover:text-rose-400 p-1">
              <Icon name="logout" className="w-4 h-4" />
            </button>
          )}
        </div>
      </div>
    </aside>
  )
}

function Topbar({ title, notifications, unreadCount, onNotificationRead, onMarkAllRead, onOpenProfile }) {
  const { user, darkMode, setDarkMode } = useAuth()
  const [notifOpen, setNotifOpen] = useState(false)
  const notifRef = useRef(null)

  // Close notifications popover on click outside
  useEffect(() => {
    function handleClickOutside(event) {
      if (notifRef.current && !notifRef.current.contains(event.target)) {
        setNotifOpen(false)
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  return (
    <header className="bg-white dark:bg-slate-950 border-b border-slate-200 dark:border-slate-800 px-6 py-3.5 flex items-center justify-between sticky top-0 z-40 transition-colors">
      <div className="flex items-center gap-3">
        <h2 className="font-bold text-slate-900 dark:text-white text-base tracking-tight">{title}</h2>
      </div>

      <div className="flex items-center gap-3">
        {/* Theme Toggle (Dark / Light) */}
        <button
          type="button"
          onClick={() => setDarkMode(!darkMode)}
          title={darkMode ? "Switch to light mode" : "Switch to dark mode"}
          className="p-2 rounded-xl text-slate-500 hover:text-slate-800 dark:text-slate-400 dark:hover:text-white hover:bg-slate-100 dark:hover:bg-slate-900 transition"
        >
          <Icon name={darkMode ? 'sun' : 'moon'} className="w-4 h-4" />
        </button>

        {/* Real-time Notifications Bell with Badge */}
        <div className="relative" ref={notifRef}>
          <button
            type="button"
            onClick={() => setNotifOpen(!notifOpen)}
            className="p-2 rounded-xl text-slate-500 hover:text-slate-800 dark:text-slate-400 dark:hover:text-white hover:bg-slate-100 dark:hover:bg-slate-900 transition relative"
            title="Notifications"
          >
            <Icon name="bell" className="w-4 h-4" />
            {unreadCount > 0 && (
              <span className="absolute top-1 right-1 w-4 h-4 rounded-full bg-rose-600 text-white text-[10px] font-extrabold flex items-center justify-center animate-pulse">
                {unreadCount > 9 ? '9+' : unreadCount}
              </span>
            )}
          </button>

          {/* Notifications Popover */}
          {notifOpen && (
            <div className="absolute right-0 mt-2 w-80 sm:w-96 rounded-2xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-2xl z-50 overflow-hidden animate-fadeIn">
              <div className="flex items-center justify-between px-4 py-3 border-b border-slate-100 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-900/50">
                <div className="flex items-center gap-2">
                  <span className="text-xs font-bold text-slate-900 dark:text-white">Live Notifications</span>
                  {unreadCount > 0 && (
                    <span className="rounded-full bg-rose-100 dark:bg-rose-950/60 text-rose-700 dark:text-rose-300 px-2 py-0.2 text-[10px] font-bold">
                      {unreadCount} new
                    </span>
                  )}
                </div>
                {unreadCount > 0 && (
                  <button
                    type="button"
                    onClick={onMarkAllRead}
                    className="text-[11px] text-brand-600 dark:text-brand-400 hover:underline font-semibold"
                  >
                    Mark all read
                  </button>
                )}
              </div>

              <div className="max-h-80 overflow-y-auto divide-y divide-slate-100 dark:divide-slate-800 text-xs">
                {notifications.length === 0 ? (
                  <div className="p-8 text-center text-slate-400 text-xs">
                    No notifications yet. You're completely up to date!
                  </div>
                ) : (
                  notifications.map((n) => (
                    <div
                      key={n.id}
                      onClick={() => {
                        onNotificationRead(n.id)
                        if (n.bug_id) {
                          window.location.hash = `#/bugs/${n.bug_id}`
                          setNotifOpen(false)
                        }
                      }}
                      className={`p-3.5 hover:bg-slate-50 dark:hover:bg-slate-800/60 transition cursor-pointer flex items-start gap-3 ${
                        n.is_read ? 'opacity-70' : 'bg-brand-50/20 dark:bg-brand-950/10'
                      }`}
                    >
                      <div className={`w-7 h-7 rounded-lg flex items-center justify-center shrink-0 mt-0.5 ${
                        n.type === 'danger' ? 'bg-rose-100 text-rose-600 dark:bg-rose-950 dark:text-rose-400' :
                        n.type === 'success' ? 'bg-emerald-100 text-emerald-600 dark:bg-emerald-950 dark:text-emerald-400' :
                        n.type === 'warning' ? 'bg-amber-100 text-amber-600 dark:bg-amber-950 dark:text-amber-400' :
                        'bg-brand-100 text-brand-600 dark:bg-brand-950 dark:text-brand-400'
                      }`}>
                        <Icon name={n.type === 'danger' ? 'alert' : n.type === 'success' ? 'check-circle' : 'bell'} className="w-3.5 h-3.5" />
                      </div>
                      <div className="min-w-0 flex-1">
                        <div className="font-bold text-slate-900 dark:text-white flex items-center justify-between">
                          <span className="truncate">{n.title}</span>
                          <span className="text-[10px] text-slate-400 font-normal shrink-0 ml-2">{fmtRelative(n.created_at)}</span>
                        </div>
                        <p className="text-slate-600 dark:text-slate-300 text-[11px] leading-relaxed mt-0.5">{n.message}</p>
                      </div>
                    </div>
                  ))
                )}
              </div>
            </div>
          )}
        </div>

        {/* User Account / Profile Button */}
        <button
          type="button"
          onClick={onOpenProfile}
          className="flex items-center gap-2 pl-2 rounded-xl hover:bg-slate-100 dark:hover:bg-slate-900 p-1.5 transition"
        >
          <div className="w-7 h-7 rounded-full bg-brand-600 text-white text-xs font-bold flex items-center justify-center">
            {user.name[0]}
          </div>
          <span className="text-xs font-bold text-slate-800 dark:text-slate-200 hidden sm:inline">
            {user.name.split(' ')[0]}
          </span>
        </button>
      </div>
    </header>
  )
}

function ProfileModal({ open, onClose, user, onUserUpdated }) {
  const [name, setName] = useState(user.name)
  const [currentPassword, setCurrentPassword] = useState('')
  const [newPassword, setNewPassword] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    if (open) {
      setName(user.name)
      setCurrentPassword('')
      setNewPassword('')
      setError('')
    }
  }, [open, user])

  async function handleSave(e) {
    e.preventDefault()
    setBusy(true)
    setError('')
    try {
      const res = await updateProfile({
        name,
        current_password: currentPassword || undefined,
        new_password: newPassword || undefined
      })
      onUserUpdated(res.user)
      toast('Profile updated successfully')
      onClose()
    } catch (err) {
      setError(err.message)
    } finally {
      setBusy(false)
    }
  }

  return (
    <Modal open={open} onClose={onClose} title="User Profile &amp; Settings">
      <form onSubmit={handleSave} className="space-y-4">
        <div>
          <label className="label">Registered Email (Read-Only)</label>
          <input className="input bg-slate-100 dark:bg-slate-800/80 cursor-not-allowed" disabled value={user.email} />
        </div>
        <div>
          <label className="label">Assigned Role (Read-Only)</label>
          <div className="font-bold text-xs uppercase tracking-wider text-brand-600 dark:text-brand-400 capitalize">
            {user.role}
          </div>
        </div>
        <div>
          <label className="label">Display Name *</label>
          <input className="input" required value={name} onChange={(e) => setName(e.target.value)} />
        </div>

        <div className="pt-3 border-t border-slate-100 dark:border-slate-800 space-y-3">
          <div className="text-xs font-bold text-slate-700 dark:text-slate-300">Change Password (optional)</div>
          <div>
            <label className="label">Current Password</label>
            <input
              className="input"
              type="password"
              value={currentPassword}
              onChange={(e) => setCurrentPassword(e.target.value)}
              placeholder="••••••••"
            />
          </div>
          <div>
            <label className="label">New Password (min 6 characters)</label>
            <input
              className="input"
              type="password"
              value={newPassword}
              onChange={(e) => setNewPassword(e.target.value)}
              placeholder="••••••••"
            />
          </div>
        </div>

        {error && <div className="text-xs text-rose-600 dark:text-rose-400">{error}</div>}

        <div className="flex justify-end gap-2 pt-2">
          <button type="button" onClick={onClose} className="btn-secondary">Cancel</button>
          <button className="btn-primary" disabled={busy}>
            {busy ? 'Saving…' : 'Save Changes'}
          </button>
        </div>
      </form>
    </Modal>
  )
}
