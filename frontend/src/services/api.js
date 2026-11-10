// Enhanced API client for BugTrack (Flask backend at /api)
let token = localStorage.getItem('bt_token') || ''
let toastHandler = null

export function setToken(t) {
  token = t || ''
  if (token) localStorage.setItem('bt_token', token)
  else localStorage.removeItem('bt_token')
}
export function getToken() { return token }

export function setToastHandler(fn) { toastHandler = fn }
export function toast(msg, type = 'success') {
  if (toastHandler) toastHandler(msg, type)
}

export async function api(path, { method = 'GET', body } = {}) {
  const headers = { 'Content-Type': 'application/json' }
  if (token) headers.Authorization = 'Bearer ' + token
  const res = await fetch('/api' + path, {
    method,
    headers,
    body: body ? JSON.stringify(body) : undefined
  })
  if (res.status === 401) {
    setToken('')
    localStorage.removeItem('bt_user')
    window.location.hash = '#/login'
    throw new Error('Session expired. Please log in again.')
  }
  const data = await res.json().catch(() => ({}))
  if (!res.ok) throw new Error(data.error || 'Request failed (' + res.status + ')')
  return data
}

export async function apiBlob(path) {
  const headers = {}
  if (token) headers.Authorization = 'Bearer ' + token
  const res = await fetch('/api' + path, { headers })
  if (!res.ok) {
    const data = await res.json().catch(() => ({}))
    throw new Error(data.error || 'Failed to download (' + res.status + ')')
  }
  return res.blob()
}

// Download file trigger helper
export async function downloadFile(path, filename) {
  const blob = await apiBlob(path)
  const url = window.URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  document.body.appendChild(a)
  a.click()
  a.remove()
  window.URL.revokeObjectURL(url)
}

// Notifications API
export async function fetchNotifications() {
  return api('/notifications')
}
export async function fetchUnreadCount() {
  return api('/notifications/unread-count')
}
export async function markNotificationRead(id) {
  return api(`/notifications/${id}/read`, { method: 'PUT' })
}
export async function markAllNotificationsRead() {
  return api('/notifications/read-all', { method: 'PUT' })
}

// Auth API
export async function registerUser({ name, email, password }) {
  return api('/register', { method: 'POST', body: { name, email, password } })
}
export async function forgotPassword(email) {
  return api('/forgot-password', { method: 'POST', body: { email } })
}
export async function resetPassword({ token, password }) {
  return api('/reset-password', { method: 'POST', body: { token, password } })
}
export async function updateProfile({ name, current_password, new_password }) {
  return api('/profile', { method: 'PUT', body: { name, current_password, new_password } })
}

// Datetime formatters
export function fmt(ts) {
  if (!ts) return '—'
  const d = new Date(ts.includes('T') ? ts : ts.replace(' ', 'T') + 'Z')
  if (isNaN(d)) return ts
  return d.toLocaleString(undefined, { dateStyle: 'medium', timeStyle: 'short' })
}

export function fmtDate(ts) {
  if (!ts) return '—'
  const d = new Date(ts.includes('T') ? ts : ts.replace(' ', 'T') + 'Z')
  if (isNaN(d)) return ts
  return d.toLocaleDateString(undefined, { year: 'numeric', month: 'short', day: 'numeric' })
}

export function fmtRelative(ts) {
  if (!ts) return '—'
  const d = new Date(ts.includes('T') ? ts : ts.replace(' ', 'T') + 'Z')
  if (isNaN(d)) return ts
  const diffSec = Math.floor((Date.now() - d.getTime()) / 1000)
  if (diffSec < 60) return 'just now'
  if (diffSec < 3600) return `${Math.floor(diffSec / 60)}m ago`
  if (diffSec < 86400) return `${Math.floor(diffSec / 3600)}h ago`
  if (diffSec < 604800) return `${Math.floor(diffSec / 86400)}d ago`
  return d.toLocaleDateString(undefined, { month: 'short', day: 'numeric' })
}
