// Tools → History (/tools/history): todo lo que ha cambiado en la colección, con filtros, «Undo» en cada cambio y los
// puntos de restauración automáticos (antes de restaurar una copia o importar un CSV o un mazo).
import { useEffect, useState } from 'react'
import HistoryList from './components/HistoryList'
import { historyWhen } from './lib/history'
import { api } from './lib/api'
import type { HistoryFilter, Location, RestorePointRow } from './lib/types'

function readFilter(): HistoryFilter {
  const p = new URLSearchParams(window.location.search)
  const num = (k: string) => (p.get(k) ? Number(p.get(k)) : undefined)
  return {
    q: p.get('q') ?? undefined, kind: p.get('kind') ?? undefined, source: p.get('source') ?? undefined,
    location: num('location'), card: num('card'), from: p.get('from') ?? undefined, to: p.get('to') ?? undefined,
  }
}

export default function HistoryPage() {
  const [filter, setFilter] = useState<HistoryFilter>(readFilter)
  const [typed, setTyped] = useState(filter.q ?? '')
  const [kinds, setKinds] = useState<Record<string, string>>({})
  const [locations, setLocations] = useState<Location[]>([])
  const [cardLabel, setCardLabel] = useState('')
  const [reload, setReload] = useState(0)

  useEffect(() => {
    api.history({ page_size: 1 }).then((d) => setKinds(d.kinds)).catch(() => {})
    api.locations().then(setLocations).catch(() => {})
  }, [])
  useEffect(() => {
    if (!filter.card) return
    api
      .card(filter.card)
      .then((c) => setCardLabel(`${c.card_number} ${c.name}`))
      .catch(() => setCardLabel(`#${filter.card}`))
  }, [filter.card])
  // El texto se aplica al dejar de escribir.
  useEffect(() => {
    const t = window.setTimeout(() => setFilter((f) => (f.q === (typed.trim() || undefined) ? f : { ...f, q: typed.trim() || undefined })), 350)
    return () => window.clearTimeout(t)
  }, [typed])
  // Los filtros, en la dirección (para volver o compartir el enlace).
  useEffect(() => {
    const p = new URLSearchParams()
    for (const [k, v] of Object.entries(filter)) if (v != null && v !== '') p.set(k, String(v))
    window.history.replaceState(null, '', `/tools/history${p.size ? `?${p}` : ''}`)
  }, [filter])

  const set = (patch: Partial<HistoryFilter>) => setFilter((f) => ({ ...f, ...patch }))
  const active = Object.values(filter).some((v) => v != null && v !== '')

  return (
    <main className="tools-page hx-page">
      <header>
        <p className="muted small">
          <a className="link" href="/tools">
            Tools
          </a>{' '}
          ›
        </p>
        <h1>History</h1>
        <p className="muted">
          Every change to your collection: copies added, removed or moved, decks, binders and imports. Open a change to see what
          moved where and undo it: each copy goes back to where it was.
        </p>
      </header>

      <section className="tools-card">
        <div className="hx-filters">
          <input className="input" type="search" value={typed} onChange={(e) => setTyped(e.target.value)} placeholder="Search a card (name or number) or a change…" />
          <select className="input" value={filter.kind ?? ''} onChange={(e) => set({ kind: e.target.value || undefined })} aria-label="Type of change">
            <option value="">All types</option>
            {Object.entries(kinds)
              .filter(([k]) => k !== 'restore_point')
              .map(([k, label]) => (
                <option key={k} value={k}>
                  {label}
                </option>
              ))}
          </select>
          <select
            className="input"
            value={filter.location ?? ''}
            onChange={(e) => set({ location: e.target.value ? Number(e.target.value) : undefined })}
            aria-label="Location or deck"
          >
            <option value="">All locations</option>
            {locations.map((l) => (
              <option key={l.id} value={l.id}>
                {l.name}
              </option>
            ))}
          </select>
          <select className="input" value={filter.source ?? ''} onChange={(e) => set({ source: e.target.value || undefined })} aria-label="From">
            <option value="">Web, scanner and admin</option>
            <option value="web">Web</option>
            <option value="scanner">Scanner</option>
            <option value="admin">Admin</option>
          </select>
          <label className="small hx-date">
            From <input className="input" type="date" value={filter.from ?? ''} onChange={(e) => set({ from: e.target.value || undefined })} />
          </label>
          <label className="small hx-date">
            To <input className="input" type="date" value={filter.to ?? ''} onChange={(e) => set({ to: e.target.value || undefined })} />
          </label>
        </div>
        {(filter.card || active) && (
          <div className="hx-active">
            {filter.card && (
              <span className="hx-tag">
                Card: {cardLabel || '…'}{' '}
                <button className="link small" onClick={() => set({ card: undefined })} aria-label="Remove the card filter">
                  ✕
                </button>
              </span>
            )}
            {active && (
              <button
                className="link small"
                onClick={() => {
                  setTyped('')
                  setFilter({})
                }}
              >
                ✕ Clear filters
              </button>
            )}
          </div>
        )}
        <HistoryList filter={filter} reloadKey={reload} empty={active ? 'No changes match these filters.' : 'No changes yet: they show up here from now on.'} />
      </section>

      <RestorePoints onRestored={() => setReload((r) => r + 1)} />
    </main>
  )
}

function RestorePoints({ onRestored }: { onRestored: () => void }) {
  const [points, setPoints] = useState<RestorePointRow[] | null>(null)
  const [days, setDays] = useState(90)
  const [asking, setAsking] = useState<{ id: number; changes: number; added: number; removed: number; cards: number } | null>(null)
  const [busy, setBusy] = useState(false)
  const [msg, setMsg] = useState('')
  const load = () =>
    api
      .restorePoints()
      .then((d) => {
        setPoints(d.results)
        setDays(d.days)
      })
      .catch(() => setPoints([]))
  useEffect(() => {
    void load()
  }, [])
  const ask = (id: number) => {
    setBusy(true)
    setMsg('')
    api
      .restorePointPreview(id)
      .then(setAsking)
      .catch((e: Error) => setMsg(e.message))
      .finally(() => setBusy(false))
  }
  const restore = (id: number) => {
    setBusy(true)
    api
      .restoreToPoint(id)
      .then(() => {
        setAsking(null)
        setMsg('✓ Your collection is back to that point. You can undo this in the history above.')
        void load()
        onRestored()
      })
      .catch((e: Error) => setMsg(e.message))
      .finally(() => setBusy(false))
  }
  return (
    <section className="tools-card">
      <h2>Restore points</h2>
      <p className="muted small">
        A full copy of your collection saved automatically just before restoring a backup or importing a CSV or a deck. Kept for{' '}
        {days} days. Use it when something went very wrong: it puts everything back as it was at that moment.
      </p>
      {points && points.length === 0 && <p className="muted small">None yet.</p>}
      {msg && <p className="small">{msg}</p>}
      <ul className="hx-points">
        {points?.map((p) => (
          <li key={p.id}>
            <span>
              <strong>{historyWhen(p.created_at)}</strong> · before “{p.reason}”
            </span>
            {asking?.id === p.id ? (
              <div className="hx-confirm">
                <p>
                  {asking.changes === 0
                    ? 'Your collection is already exactly like that.'
                    : `Going back changes ${asking.cards} cards (${asking.added ? `+${asking.added} ` : ''}${asking.removed ? `−${asking.removed} ` : ''}copies, plus moves) and undoes everything done since, including later changes.`}
                </p>
                <div>
                  {asking.changes > 0 && (
                    <button className="btn primary small" disabled={busy} onClick={() => restore(p.id)}>
                      {busy ? 'Restoring…' : 'Yes, go back to this point'}
                    </button>
                  )}
                  <button className="btn small" onClick={() => setAsking(null)} disabled={busy}>
                    Cancel
                  </button>
                </div>
              </div>
            ) : (
              <button className="btn small" disabled={busy} onClick={() => ask(p.id)}>
                Restore to this point…
              </button>
            )}
          </li>
        ))}
      </ul>
    </section>
  )
}
