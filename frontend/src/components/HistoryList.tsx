// Histórico de cambios de la colección: la lista de acciones (en Tools → History, en la ficha de una carta y en la vista
// de un mazo), el detalle de cada una (qué copias cambiaron, de dónde a dónde) y «Undo» con su comprobación.
import { useCallback, useEffect, useState } from 'react'
import { api, ApiError } from '../lib/api'
import type { HistoryActivity, HistoryDetail, HistoryFilter, UndoCheck } from '../lib/types'
import { cardThumb } from '../lib/types'
import { historyWhen } from '../lib/history'


const SOURCE_ICON: Record<string, string> = { web: '', scanner: '📷 ', admin: '⚙️ ' }

interface Props {
  filter: HistoryFilter
  /** Cuántas por página (por defecto 30). */
  pageSize?: number
  /** Sin paginación: solo las últimas `pageSize` y un enlace a la página completa. */
  compact?: boolean
  /** Algo se deshizo: para recargar lo que dependa de la colección. */
  onChanged?: () => void
  /** Para recargar desde fuera (al cambiar de filtros, tras volver a un punto…). */
  reloadKey?: number
  empty?: string
}

export default function HistoryList({ filter, pageSize = 30, compact, onChanged, reloadKey = 0, empty = 'No changes yet.' }: Props) {
  const [data, setData] = useState<{ results: HistoryActivity[]; count: number; pages: number } | null>(null)
  const [page, setPage] = useState(1)
  const [error, setError] = useState('')
  const [tick, setTick] = useState(0)
  const key = JSON.stringify(filter)
  const [lastKey, setLastKey] = useState(key)
  if (key !== lastKey) {
    setLastKey(key)
    setPage(1)
  }

  useEffect(() => {
    const ctrl = new AbortController()
    api
      .history({ ...(JSON.parse(key) as HistoryFilter), page, page_size: pageSize }, ctrl.signal)
      .then((d) => {
        setData(d)
        setError('')
      })
      .catch((e: Error) => e.name !== 'AbortError' && setError(e.message))
    return () => ctrl.abort()
  }, [key, page, pageSize, tick, reloadKey])

  const changed = useCallback(() => {
    setTick((t) => t + 1)
    onChanged?.()
  }, [onChanged])

  if (error) return <p className="error small">{error}</p>
  if (!data) return <p className="muted small">Loading the history…</p>
  if (data.results.length === 0) return <p className="muted small">{empty}</p>
  const params = new URLSearchParams(Object.entries(filter).filter(([, v]) => v != null && v !== '').map(([k, v]) => [k, String(v)]))
  return (
    <div className="hx">
      <ul className="hx-list">
        {data.results.map((a) => (
          <HistoryRow key={`${a.id}-${a.updated_at}-${a.undone_at ?? ''}`} activity={a} onChanged={changed} />
        ))}
      </ul>
      {compact ? (
        data.count > data.results.length && (
          <a className="link small" href={`/tools/history${params.size ? `?${params}` : ''}`}>
            See all {data.count} changes →
          </a>
        )
      ) : (
        data.pages > 1 && (
          <div className="hx-pager">
            <button className="btn small" disabled={page <= 1} onClick={() => setPage(page - 1)}>
              ‹ Newer
            </button>
            <span className="muted small">
              Page {page} of {data.pages} · {data.count} changes
            </span>
            <button className="btn small" disabled={page >= data.pages} onClick={() => setPage(page + 1)}>
              Older ›
            </button>
          </div>
        )
      )}
    </div>
  )
}

function counts(a: HistoryActivity) {
  const out: string[] = []
  if (a.added) out.push(`+${a.added}`)
  if (a.removed) out.push(`−${a.removed}`)
  if (a.moved) out.push(`⇄ ${a.moved}`)
  return out
}

function HistoryRow({ activity: a, onChanged }: { activity: HistoryActivity; onChanged: () => void }) {
  const [open, setOpen] = useState(false)
  const [detail, setDetail] = useState<HistoryDetail | null>(null)
  const [check, setCheck] = useState<UndoCheck | null>(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const toggle = () => {
    if (!open && !detail) api.historyDetail(a.id).then(setDetail).catch((e: Error) => setError(e.message))
    setOpen(!open)
    setCheck(null)
  }
  // Qué se deshace: el propio cambio («Undo»), o para rehacer, el «Undo» que lo deshizo («Redo»).
  const isRedo = a.kind === 'undo' || (!!a.undone_at && a.redo_id != null)
  const target = a.kind !== 'undo' && a.undone_at && a.redo_id != null ? a.redo_id : a.id
  const askUndo = () => {
    setBusy(true)
    setError('')
    api
      .undoCheck(target)
      .then(setCheck)
      .catch((e: Error) => setError(e.message))
      .finally(() => setBusy(false))
  }
  const doUndo = () => {
    setBusy(true)
    setError('')
    api
      .undo(target)
      .then(() => {
        setCheck(null)
        onChanged()
      })
      .catch((e: Error) => {
        setError(e.message)
        if (e instanceof ApiError && e.status === 409) askUndo()
      })
      .finally(() => setBusy(false))
  }
  const undoable = a.kind === 'undo' ? !a.undone_at : !a.undone_at || a.redo_id != null
  return (
    <li className={`hx-row ${a.undone_at ? 'undone' : ''} ${a.kind === 'undo' || a.kind === 'redo' ? 'is-undo' : ''}`}>
      <button type="button" className="hx-head" onClick={toggle} aria-expanded={open}>
        <span className="hx-kind">{a.kind_label}</span>
        <span className="hx-title">
          {SOURCE_ICON[a.source]}
          {a.title.replace(new RegExp(`^${a.kind_label.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}: `), '')}
        </span>
        <span className="hx-meta">
          {counts(a).map((c) => (
            <span key={c} className={`hx-count ${c[0] === '+' ? 'in' : c[0] === '−' ? 'out' : 'move'}`}>
              {c}
            </span>
          ))}
          {a.restore_point && <span className="hx-tag" title="A restore point was saved just before this">⟲ point</span>}
          {a.undone_at && <span className="hx-tag">undone</span>}
          <span className="muted small">{historyWhen(a.updated_at)}</span>
        </span>
      </button>
      {open && (
        <div className="hx-body">
          {!detail && !error && <p className="muted small">Loading…</p>}
          {detail && <HistoryChanges detail={detail} />}
          {error && <p className="error small">{error}</p>}
          {undoable && !check && (
            <button className="btn small" onClick={askUndo} disabled={busy}>
              {isRedo ? '↷ Redo…' : '↶ Undo…'}
            </button>
          )}
          {check && (
            <div className={`hx-confirm ${check.ok ? '' : 'blocked'}`}>
              {check.ok ? (
                <>
                  {isRedo ? (
                    <p>
                      The change {a.kind === 'undo' ? `“${a.undo_of?.title ?? ''}”` : 'above'} is applied again, exactly as it was
                      before you undid it. This is saved as a new change, too.
                    </p>
                  ) : (
                    <p>
                      Everything above goes back to how it was before
                      {a.added || a.removed || a.moved ? ': each copy returns to where it was, binder positions included' : ''}. This
                      is saved as a new change, too.
                    </p>
                  )}
                  <div>
                    <button className="btn primary small" onClick={doUndo} disabled={busy}>
                      {busy ? (isRedo ? 'Redoing…' : 'Undoing…') : isRedo ? 'Yes, redo it' : 'Yes, undo it'}
                    </button>
                    <button className="btn small" onClick={() => setCheck(null)} disabled={busy}>
                      Cancel
                    </button>
                  </div>
                </>
              ) : (
                <>
                  <p>
                    ⚠ {check.conflict_rows} of these changes were modified afterwards, so undoing this now would overwrite them.
                    Undo these first (newest first):
                  </p>
                  <ul>
                    {check.later.map((l) => (
                      <li key={l.id}>
                        {l.title} <span className="muted small">· {historyWhen(l.updated_at)}</span>
                      </li>
                    ))}
                  </ul>
                  <button className="btn small" onClick={() => setCheck(null)}>
                    OK
                  </button>
                </>
              )}
            </div>
          )}
        </div>
      )}
    </li>
  )
}

/** El detalle: carta a carta, cuántas copias había en cada sitio antes y después (y su posición si cambió). */
function HistoryChanges({ detail }: { detail: HistoryDetail }) {
  const [all, setAll] = useState(false)
  const shown = all ? detail.copies : detail.copies.slice(0, 12)
  return (
    <div className="hx-changes">
      {detail.undo_of && <p className="muted small">Undid: {detail.undo_of.title}</p>}
      {detail.other.length > 0 && (
        <ul className="hx-other">
          {detail.other.map((o, i) => (
            <li key={i}>{o}</li>
          ))}
        </ul>
      )}
      {shown.length > 0 && (
        <table className="hx-table">
          <tbody>
            {shown.map((row) => (
              <tr key={row.card.id}>
                <td className="hx-card">
                  {row.card.image_url && <img src={cardThumb(row.card as never)} alt="" loading="lazy" referrerPolicy="no-referrer" />}
                  <span>
                    <small>{row.card.card_number}</small>
                    {row.card.name}
                  </span>
                </td>
                <td>
                  {row.changes.map((c) => {
                    const d = c.after - c.before
                    return (
                      <div key={`${c.location_id}-${c.fake}`} className="hx-loc">
                        <span className={`hx-count ${d > 0 ? 'in' : d < 0 ? 'out' : 'move'}`}>
                          {d > 0 ? `+${d}` : d < 0 ? `−${-d}` : '·'}
                        </span>
                        <strong>{c.location}</strong>
                        {c.fake && <span className="hx-tag">fake</span>}
                        <span className="muted small">
                          {c.before} → {c.after}
                        </span>
                        {c.notes_before !== c.notes_after && (
                          <span className="hx-notes" title={`Before:\n${c.notes_before}\n\nAfter:\n${c.notes_after}`}>
                            {c.notes_before ? c.notes_before.split('\n').join(' · ') : '—'} ⟶ {c.notes_after ? c.notes_after.split('\n').join(' · ') : '—'}
                          </span>
                        )}
                      </div>
                    )
                  })}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
      {detail.copies.length > 12 && !all && (
        <button className="link small" onClick={() => setAll(true)}>
          Show all {detail.copies.length} cards
        </button>
      )}
    </div>
  )
}
