// Herramientas (/tools): lo de mantenimiento, fuera de las páginas de uso diario.
// Copias de seguridad y CSV de la colección, estado del sistema, sincronizaciones con Bandai y últimos errores.
import { useEffect, useState } from 'react'
import CsvImport from './components/CsvImport'
import HistoryList from './components/HistoryList'
import RestoreBackup from './components/RestoreBackup'
import { api, COLLECTION_BACKUP_URL, COLLECTION_CSV_URL } from './lib/api'
import type { ErrorEntry, HealthCheck, SyncRunRow } from './lib/types'

const ago = (iso: string | null) => {
  if (!iso) return '—'
  const s = Math.max(0, (Date.now() - new Date(iso).getTime()) / 1000)
  if (s < 90) return 'just now'
  if (s < 5400) return `${Math.round(s / 60)} min ago`
  if (s < 129600) return `${Math.round(s / 3600)} h ago`
  return `${Math.round(s / 86400)} days ago`
}
const when = (iso: string) => new Date(iso).toLocaleString('en-GB', { dateStyle: 'medium', timeStyle: 'short' })
const duration = (a: string, b: string | null) => {
  if (!b) return '—'
  const s = Math.round((new Date(b).getTime() - new Date(a).getTime()) / 1000)
  return s < 120 ? `${s} s` : `${Math.round(s / 60)} min`
}

export default function ToolsPage() {
  const [done, setDone] = useState('')
  return (
    <main className="tools-page">
      <header>
        <h1>Tools</h1>
        <p className="muted">Backups, imports and how the system is doing.</p>
      </header>

      <section className="tools-card">
        <div className="tools-card-head">
          <h2>History</h2>
          <a className="link small" href="/tools/history">
            Open the full history →
          </a>
        </div>
        <p className="muted small">The latest changes to your collection. Open one to see what moved where, and undo it.</p>
        <HistoryList filter={{}} pageSize={6} compact empty="No changes yet: they show up here from now on." />
      </section>

      <section className="tools-card">
        <h2>Collection data</h2>
        <div className="tools-actions">
          <div>
            <a className="btn" href={COLLECTION_BACKUP_URL} download>
              Download backup
            </a>
            <p className="muted small">A JSON with your locations, decks, wants and every copy. Keep it somewhere safe.</p>
          </div>
          <div>
            <RestoreBackup onDone={() => setDone('Backup restored.')} />
            <p className="muted small">Replaces your collection with a backup (you see a preview first).</p>
          </div>
          <div>
            <a className="btn" href={COLLECTION_CSV_URL} download>
              Download CSV
            </a>
            <p className="muted small">Your collection as a spreadsheet, for Excel or Google Sheets.</p>
          </div>
          <div>
            <CsvImport onDone={() => setDone('CSV imported.')} />
            <p className="muted small">Adds copies from a CSV (you see a preview first).</p>
          </div>
        </div>
        {done && <p className="tools-done">✓ {done}</p>}
      </section>

      <SystemStatus />
      <SyncHistory />
      <RecentErrors />
    </main>
  )
}

function SystemStatus() {
  const [checks, setChecks] = useState<HealthCheck[] | null>(null)
  const [at, setAt] = useState<string | null>(null)
  const [error, setError] = useState('')
  const load = () =>
    api
      .health()
      .then((h) => {
        setChecks(h.checks)
        setAt(h.checked_at)
        setError('')
      })
      .catch(() => setError("The server isn't responding."))
  useEffect(() => {
    void load()
    const t = window.setInterval(load, 60_000)
    return () => window.clearInterval(t)
  }, [])
  return (
    <section className="tools-card">
      <div className="tools-card-head">
        <h2>System status</h2>
        <button className="link small" onClick={load}>
          ↻ Check again {at && <span className="muted">· {ago(at)}</span>}
        </button>
      </div>
      {error && <p className="error">{error}</p>}
      {!checks && !error && <p className="muted">Checking…</p>}
      {checks && (
        <ul className="tools-checks">
          {checks.map((c) => (
            <li key={c.key} className={c.ok ? 'ok' : c.kind === 'critical' ? 'down' : c.kind === 'optional' ? 'off' : 'warn'}>
              <span className="dot" aria-hidden />
              <strong>{c.label}</strong>
              <span className="muted">{c.detail}</span>
            </li>
          ))}
        </ul>
      )}
    </section>
  )
}

const SYNC_STATUS: Record<string, string> = { running: 'Running', success: 'OK', partial: 'With failures', failed: 'Failed' }

function SyncHistory() {
  const [runs, setRuns] = useState<SyncRunRow[] | null>(null)
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const [confirmFull, setConfirmFull] = useState(false)
  const [notice, setNotice] = useState('')
  // Tras lanzar una, se sigue mirando un rato hasta que aparece (la tarea tarda unos segundos en arrancar).
  const [waitUntil, setWaitUntil] = useState(0)
  const load = () =>
    api
      .syncRuns()
      .then((r) => {
        setRuns(r.results.slice(0, 10))
        setError('')
      })
      .catch((e: Error) => setError(e.message))
  useEffect(() => {
    void load()
  }, [])
  const running = runs?.some((r) => r.status === 'running') ?? false
  const watching = running || waitUntil > 0
  useEffect(() => {
    if (!watching) return
    const t = window.setInterval(() => {
      void load()
      if (Date.now() > waitUntil) setWaitUntil(0)
    }, 5000)
    return () => window.clearInterval(t)
  }, [watching, waitUntil])
  const start = (full: boolean) => {
    setBusy(true)
    setConfirmFull(false)
    setNotice('')
    api
      .startSync(full)
      .then(() => {
        setNotice(full ? 'Full sync started: it takes about an hour and a half.' : 'Sync started: it takes a few seconds.')
        setWaitUntil(Date.now() + 60_000)
      })
      .catch((e: Error) => setNotice(e.message))
      .finally(() => setBusy(false))
  }
  return (
    <section className="tools-card">
      <div className="tools-card-head">
        <h2>Bandai sync</h2>
        <a className="link small" href="/news">
          See what changed →
        </a>
      </div>
      <p className="muted small">Runs on its own every day. You can also start one now:</p>
      <div className="tools-sync-actions">
        <div>
          <button className="btn primary" disabled={busy || running} onClick={() => start(false)}>
            ↻ Sync new cards
          </button>
          <p className="muted small">Only cards that aren't in the catalog yet. A few seconds.</p>
        </div>
        <div>
          {confirmFull ? (
            <div className="tools-confirm" role="alertdialog" aria-label="Confirm full sync">
              <p>Download all {runs?.[0]?.listed ? runs[0].listed.toLocaleString('en-GB') : ''} cards again? It takes about an hour and a half.</p>
              <div>
                <button className="btn primary" disabled={busy} onClick={() => start(true)}>
                  Yes, full sync
                </button>
                <button className="btn" onClick={() => setConfirmFull(false)}>
                  Cancel
                </button>
              </div>
            </div>
          ) : (
            <>
              <button className="btn" disabled={busy || running} onClick={() => setConfirmFull(true)}>
                Full sync…
              </button>
              <p className="muted small">Every card again: picks up text, image and errata changes. About 1.5 h.</p>
            </>
          )}
        </div>
      </div>
      {running && <p className="tools-running">⏳ A sync is running…</p>}
      {notice && !running && <p className="small">{notice}</p>}
      <p className="muted small">The last 10 runs:</p>
      {error && <p className="error">{error}</p>}
      {runs && runs.length === 0 && <p className="muted">No syncs yet.</p>}
      {runs && runs.length > 0 && (
        <div className="tools-table-wrap">
          <table className="tools-table">
            <thead>
              <tr>
                <th>Started</th>
                <th>Kind</th>
                <th>Result</th>
                <th>Took</th>
                <th className="num">Listed</th>
                <th className="num">New</th>
                <th className="num">Updated</th>
                <th className="num">Failed</th>
              </tr>
            </thead>
            <tbody>
              {runs.map((r) => (
                <tr key={r.id} title={r.error || undefined}>
                  <td>{when(r.started_at)}</td>
                  <td>{r.full ? 'Full' : 'New cards'}</td>
                  <td>
                    <span className={`tools-status ${r.status}`}>{SYNC_STATUS[r.status] ?? r.status}</span>
                  </td>
                  <td>{duration(r.started_at, r.finished_at)}</td>
                  <td className="num">{r.listed}</td>
                  <td className="num">{r.created}</td>
                  <td className="num">{r.updated}</td>
                  <td className="num">{r.failed || ''}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  )
}

function RecentErrors() {
  const [data, setData] = useState<{ errors: ErrorEntry[]; open: number } | null>(null)
  const [error, setError] = useState('')
  const [onlyOpen, setOnlyOpen] = useState(true)
  useEffect(() => {
    api
      .recentErrors()
      .then(setData)
      .catch((e: Error) => setError(e.message))
  }, [])
  const list = data ? data.errors.filter((e) => !onlyOpen || !e.resolved_at) : []
  return (
    <section className="tools-card">
      <div className="tools-card-head">
        <h2>
          Recent errors {data && data.open > 0 && <span className="tools-badge">{data.open} open</span>}
        </h2>
        <label className="small">
          <input type="checkbox" checked={onlyOpen} onChange={(e) => setOnlyOpen(e.target.checked)} /> Only open ones
        </label>
      </div>
      <p className="muted small">The same error is grouped. Mark them as resolved in the admin; you also get them on Telegram.</p>
      {error && <p className="error">{error}</p>}
      {data && list.length === 0 && <p className="tools-done">✓ No {onlyOpen ? 'open ' : ''}errors.</p>}
      <ul className="tools-errors">
        {list.map((e) => (
          <li key={e.id} className={e.resolved_at ? 'resolved' : ''}>
            <details>
              <summary>
                <span className="tools-err-head">
                  <span className={`tools-source ${e.source}`}>{e.source_label}</span>
                  <strong>{e.kind}</strong>
                  {e.count > 1 && <span className="tools-badge">×{e.count}</span>}
                  {e.resolved_at && <span className="muted small">resolved</span>}
                  <span className="muted small tools-err-when">{ago(e.last_seen)}</span>
                </span>
                <span className="tools-err-msg">{e.message}</span>
              </summary>
              <dl>
                {e.request && (
                  <>
                    <dt>Request</dt>
                    <dd>{e.request}</dd>
                  </>
                )}
                {e.where && (
                  <>
                    <dt>Where</dt>
                    <dd>{e.where}</dd>
                  </>
                )}
                <dt>Seen</dt>
                <dd>
                  {e.count} times · first {when(e.first_seen)} · last {when(e.last_seen)}
                </dd>
              </dl>
              {e.traceback && <pre>{e.traceback}</pre>}
            </details>
          </li>
        ))}
      </ul>
    </section>
  )
}
