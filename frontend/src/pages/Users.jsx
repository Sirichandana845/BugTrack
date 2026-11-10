import { useEffect, useState } from 'react'
import { api, toast } from '../services/api'
import { Badge, Modal, PageHeader, Spinner, EmptyState } from '../components/ui'
import Icon from '../components/Icon'

export default function Users() {
  const [users, setUsers] = useState(null)
  const [open, setOpen] = useState(false)
  const [form, setForm] = useState({ name: '', email: '', password: '', role: 'developer' })
  const [busy, setBusy] = useState(false)

  const load = () => api('/users').then((d) => setUsers(d.users)).catch(() => {})
  useEffect(load, [])

  async function submit(e) {
    e.preventDefault()
    setBusy(true)
    try {
      await api('/users', { method: 'POST', body: form })
      toast('User created')
      setOpen(false)
      setForm({ name: '', email: '', password: '', role: 'developer' })
      load()
    } catch (err) { toast(err.message, 'error') } finally { setBusy(false) }
  }

  async function del(u) {
    if (!window.confirm(`Delete ${u.name}?`)) return
    try { await api(`/users/${u.id}`, { method: 'DELETE' }); toast('User deleted'); load() }
    catch (err) { toast(err.message, 'error') }
  }

  if (!users) return <Spinner />

  return (
    <div>
      <PageHeader title="Manage Users" subtitle="Admin only — add team members or adjust roles."
        actions={<button className="btn-primary" onClick={() => setOpen(true)}><Icon name="plus" className="w-4 h-4" />Add User</button>} />

      <div className="card overflow-hidden">
        {users.length === 0 ? <EmptyState message="No users yet." /> : (
          <div className="overflow-x-auto">
            <table className="w-full min-w-[820px]">
              <thead>
                <tr>
                  <th className="th">Name</th>
                  <th className="th">Email</th>
                  <th className="th">Role</th>
                  <th className="th">Assigned</th>
                  <th className="th">Open</th>
                  <th className="th">Resolved</th>
                  <th className="th">Critical</th>
                  <th className="th"></th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {users.map((u) => (
                  <tr key={u.id} className="hover:bg-slate-50">
                    <td className="td font-medium">{u.name}</td>
                    <td className="td">{u.email}</td>
                    <td className="td"><Badge value={u.role} kind="role" /></td>
                    <td className="td">{u.total_bugs}</td>
                    <td className="td">{u.open_bugs}</td>
                    <td className="td">{u.resolved_bugs}</td>
                    <td className="td">{u.critical_bugs}</td>
                    <td className="td">
                      <button onClick={() => del(u)} className="text-slate-400 hover:text-red-600" title="Delete">
                        <Icon name="x" className="w-4 h-4" />
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      <Modal open={open} onClose={() => setOpen(false)} title="Add Team Member">
        <form onSubmit={submit} className="space-y-4">
          <div>
            <label className="label">Full name</label>
            <input className="input" required value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} />
          </div>
          <div>
            <label className="label">Email</label>
            <input className="input" type="email" required value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} />
          </div>
          <div>
            <label className="label">Password</label>
            <input className="input" type="password" required minLength={6} value={form.password}
              onChange={(e) => setForm({ ...form, password: e.target.value })} />
          </div>
          <div>
            <label className="label">Role</label>
            <select className="input" value={form.role} onChange={(e) => setForm({ ...form, role: e.target.value })}>
              <option value="admin">Admin</option>
              <option value="developer">Developer</option>
              <option value="tester">Tester</option>
            </select>
          </div>
          <div className="flex justify-end gap-2">
            <button type="button" className="btn-secondary" onClick={() => setOpen(false)}>Cancel</button>
            <button className="btn-primary" disabled={busy}>{busy ? 'Saving…' : 'Create User'}</button>
          </div>
        </form>
      </Modal>
    </div>
  )
}
