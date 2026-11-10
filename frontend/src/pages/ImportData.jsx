import { useEffect, useState } from 'react'
import { api, toast } from '../services/api'
import { PageHeader, Spinner } from '../components/ui'
import Icon from '../components/Icon'

export default function ImportData() {
  const [info, setInfo] = useState(null)
  const [path, setPath] = useState('')
  const [busy, setBusy] = useState(false)
  const [result, setResult] = useState(null)

  useEffect(() => {
    api('/dataset/info').then(setInfo).catch(() => {})
  }, [])

  async function runImport() {
    setBusy(true)
    setResult(null)
    try {
      const data = await api('/dataset/import', { method: 'POST', body: { path } })
      setResult(data.summary)
      toast(`Import complete — ${data.summary.inserted} bugs`)
    } catch (e) { toast(e.message, 'error') } finally { setBusy(false) }
  }

  return (
    <div>
      <PageHeader title="Data Import" subtitle="Load the Kaggle-style dataset into BugTrack (Admin only)." />

      <div className="grid lg:grid-cols-2 gap-5">
        <div className="card p-5 space-y-4">
          <h3 className="font-semibold text-slate-800 text-sm flex items-center gap-2">
            <Icon name="download" className="w-4 h-4 text-brand-600" /> Import Dataset
          </h3>
          {!info ? <Spinner /> : (
            <>
              <p className="text-sm text-slate-600 leading-relaxed">
                The bundled sample file{' '}
                <code className="text-brand-600 bg-brand-50 rounded px-1.5 py-0.5">{info.sample_file}</code>{' '}
                {info.exists ? 'exists and is ready to import.' : 'is missing — run dataset/generate_sample_dataset.py first.'}
                Importing <b>replaces</b> the current bug data (keeps users and comments-safe history).
              </p>
              <div className="bg-slate-50 rounded-lg border border-slate-200 p-3">
                <div className="label">Sample CSV columns (Kaggle-style schema)</div>
                <div className="text-xs text-slate-500 flex flex-wrap gap-1.5">
                  {info.columns.map((c) => (
                    <span key={c} className="rounded bg-white border border-slate-200 px-1.5 py-0.5 font-mono">{c}</span>
                  ))}
                </div>
              </div>
              <div>
                <label className="label">Alternative: absolute path to a real Kaggle CSV export</label>
                <input className="input" placeholder="e.g. /home/user/Downloads/bugzilla_bug_reports.csv"
                  value={path} onChange={(e) => setPath(e.target.value)} />
                <p className="text-xs text-slate-400 mt-1.5">
                  Leave empty to import the bundled sample. Real Kaggle exports also work if they use similar columns
                  (short_desc, component, severity, priority, status, resolution, assigned_to_name, creation_time…).
                </p>
              </div>
              <div className="flex items-center gap-3">
                <button className="btn-primary" onClick={runImport} disabled={busy}>
                  <Icon name="box" className="w-4 h-4" />
                  {busy ? 'Importing…' : 'Import Dataset'}
                </button>
                {baseUrlHint()}
              </div>
              {result && (
                <div className="rounded-lg bg-green-50 border border-green-200 text-green-800 text-sm px-4 py-3">
                  <b>Import finished.</b> {result.inserted} bugs inserted, {result.skipped} rows skipped.
                  Source: <code>{result.source}</code>. Dashboard &amp; charts now reflect the dataset.
                </div>
              )}
            </>
          )}
        </div>

        <div className="card p-5 space-y-4">
          <h3 className="font-semibold text-slate-800 text-sm flex items-center gap-2">
            <Icon name="refresh" className="w-4 h-4 text-brand-600" /> Pipeline: Kaggle CSV → BugTrack
          </h3>
          <ol className="space-y-3 text-sm text-slate-600">
            {[
              ['Download', 'a Kaggle bug dataset (e.g. “Bugzilla Bug Reports” or “Software bugs reports / Eclipse” — needs a free Kaggle account/API key).'],
              ['Replace', 'dataset/kaggle_bugs.csv with the real export (or keep the bundled sample).'],
              ['Import', 'Admin → Data Import → Import Dataset (or `python import_dataset.py` from the backend folder).'],
              ['Map & clean', 'columns short_desc→title, component→module, severity/priority/status/resolution are normalized; missing fields get documented defaults.'],
              ['Explore', 'the Dashboard charts and Reports — all statistics are computed from SQLite.'],
            ].map(([step, text], i) => (
              <li key={i} className="flex gap-3">
                <span className="w-6 h-6 rounded-full bg-brand-100 text-brand-700 text-xs font-bold flex items-center justify-center shrink-0 mt-0.5">
                  {i + 1}
                </span>
                <span><b className="text-slate-800">{step}:</b> {text}</span>
              </li>
            ))}
          </ol>
          <div className="bg-amber-50 border border-amber-200 rounded-lg p-3 text-xs text-amber-800 leading-relaxed">
            <b>Honesty note:</b> the bundled CSV is a generated <b>sample</b> with the same schema — it is not the real Kaggle
            download (that requires an account) and it is not real-time data. The import pipeline itself works with real exports.
          </div>
        </div>
      </div>
    </div>
  )
}

function baseUrlHint() {
  // small helper result placeholder (kept minimal)
  return null
}
