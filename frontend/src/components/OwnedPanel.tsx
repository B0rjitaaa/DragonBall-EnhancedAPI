import { useState } from 'react'
import type { CardSummary, Location, OwnedLocation } from '../lib/types'

// Última ubicación a la que añadiste copias desde una ficha (en este navegador).
const LAST_KEY = 'dbs-last-add-location'
function lastLocation(): number | null {
  try {
    const value = Number(localStorage.getItem(LAST_KEY))
    return Number.isFinite(value) && value > 0 ? value : null
  } catch {
    return null
  }
}
function rememberLocation(id: number): void {
  try {
    localStorage.setItem(LAST_KEY, String(id))
  } catch {
    // sin almacenamiento: la próxima vez propondrá «Sin ubicar»
  }
}

export const KIND_LABELS: Record<string, string> = { deck: 'Deck', binder: 'Binder', storage: 'Storage', other: 'Other' }

/** Una fila de copias: ubicación + auténticas o falsas. */
export interface Spot {
  location: number
  fake: boolean
}

interface Props {
  card: CardSummary
  locations: Location[]
  busy: boolean
  notice?: string | null
  onAdjust: (spot: Spot, delta: number) => void
  /** Mover a otra ubicación (target.fake = spot.fake) o marcar como falsas/auténticas (misma ubicación).
   * `noteLine`: la línea de la nota (p. ej. su posición en el archivador) que se va con la copia. */
  onMove: (source: Spot, target: Spot, quantity: number, noteLine?: string) => void
  onNote: (spot: Spot, notes: string) => void
}

/** Panel de copias de la ficha (en Mi colección y en el buscador): sus copias en cada ubicación, con − / +,
 *  mover, falsas y nota, y añadir a una ubicación (la última usada). */
export default function OwnedPanel({ card, locations, busy, notice, onAdjust, onMove, onNote }: Props) {
  const owned = card.locations ?? []
  const total = card.total_quantity ?? card.quantity ?? 0
  const fakes = card.fakes ?? owned.filter((l) => l.fake).reduce((n, l) => n + l.quantity, 0)
  const free = locations.filter((l) => !owned.some((o) => o.id === l.id && !o.fake))
  // Se propone la última ubicación usada; si no, «Sin ubicar».
  const [addTo, setAddTo] = useState<number | ''>(() => {
    const last = lastLocation()
    const pick = free.find((l) => l.id === last) ?? free.find((l) => l.is_default)
    return pick ? pick.id : ''
  })
  const selected = free.some((l) => l.id === addTo) ? addTo : ''

  return (
    <section className="owned-panel" aria-label="Copies in your collection">
      <header>
        {total === 0 ? (
          <>Not in your collection</>
        ) : (
          <>
            In your collection: <strong>×{total}</strong>
          </>
        )}
        {fakes > 0 && <span className="fake-badge">{fakes === 1 ? '1 fake' : `${fakes} fakes`}</span>}
      </header>
      {notice && <p className="owned-notice">{notice}</p>}
      <ul>
        {owned.map((loc) => (
          <OwnedRow
            // Se reinicia (nota, selector) cuando cambian sus copias o su nota.
            key={`${loc.id}:${loc.fake}:${loc.quantity}:${loc.notes}`}
            loc={loc}
            others={locations.filter((l) => l.id !== loc.id)}
            busy={busy}
            onAdjust={(delta) => onAdjust({ location: loc.id, fake: loc.fake }, delta)}
            onMove={(target, qty, line) =>
              onMove({ location: loc.id, fake: loc.fake }, { location: target, fake: loc.fake }, qty, line)
            }
            onToggleFake={(line) =>
              onMove({ location: loc.id, fake: loc.fake }, { location: loc.id, fake: !loc.fake }, 1, line)
            }
            onNote={(notes) => onNote({ location: loc.id, fake: loc.fake }, notes)}
          />
        ))}
      </ul>
      {free.length > 0 && (
        <div className="owned-add">
          <span>{total === 0 ? 'Add to My collection in' : 'Add a copy to'}</span>
          <select className="input" value={selected} onChange={(e) => setAddTo(e.target.value ? Number(e.target.value) : '')}>
            <option value="">choose location…</option>
            {free.map((l) => (
              <option key={l.id} value={l.id}>
                {l.name}
              </option>
            ))}
          </select>
          <button
            className="btn"
            disabled={busy || selected === ''}
            onClick={() => {
              if (selected === '') return
              onAdjust({ location: selected, fake: false }, 1)
              rememberLocation(selected)
            }}
          >
            Add
          </button>
        </div>
      )}
    </section>
  )
}

function OwnedRow({
  loc,
  others,
  busy,
  onAdjust,
  onMove,
  onToggleFake,
  onNote,
}: {
  loc: OwnedLocation
  others: Location[]
  busy: boolean
  onAdjust: (delta: number) => void
  onMove: (target: number, quantity: number, noteLine?: string) => void
  onToggleFake: (noteLine?: string) => void
  onNote: (notes: string) => void
}) {
  const [moving, setMoving] = useState(false)
  const [target, setTarget] = useState<number | ''>('')
  const [qty, setQty] = useState(loc.quantity)
  const [notes, setNotes] = useState(loc.notes)
  // Cada línea de la nota suele ser la posición de una copia en el archivador.
  const lines = loc.notes.split('\n').map((l) => l.trim()).filter(Boolean)
  // Con varias copias y posiciones apuntadas, hay que decir cuál es la que cambia.
  const mustPick = loc.quantity > 1 && lines.length > 0
  const [picking, setPicking] = useState(false)
  const [moveLine, setMoveLine] = useState('')

  return (
    <li className={loc.fake ? 'is-fake' : ''}>
      <div className="owned-row">
        <span className="owned-name">
          {loc.name}
          {loc.kind === 'deck' ? <span className="owned-tag deck">In deck</span> : loc.kind !== 'other' && <span className="owned-tag">{KIND_LABELS[loc.kind]}</span>}
          {loc.fake && <span className="fake-badge">Fake</span>}
        </span>
        <span className="owned-qty">
          <button className="qty-btn" disabled={busy} onClick={() => onAdjust(-1)} aria-label={`Remove a${loc.fake ? ' fake' : ''} copy from ${loc.name}`}>
            −
          </button>
          <strong>{loc.quantity}</strong>
          {/* Las copias nuevas son auténticas: en una fila de falsas, + no tiene sentido. */}
          {!loc.fake && (
            <button className="qty-btn" disabled={busy} onClick={() => onAdjust(1)} aria-label={`Add a copy to ${loc.name}`}>
              +
            </button>
          )}
        </span>
        <span className="owned-actions">
          <button
            className="link small"
            disabled={busy}
            onClick={() => (mustPick ? setPicking(!picking) : onToggleFake())}
            aria-expanded={mustPick ? picking : undefined}
            title={loc.fake ? 'One of these copies is genuine' : 'One of these copies is fake'}
          >
            {loc.fake ? "It's genuine" : 'Mark as fake'}
          </button>
          {others.length > 0 && (
            <button className="link small" onClick={() => setMoving(!moving)} aria-expanded={moving}>
              Move…
            </button>
          )}
        </span>
      </div>
      {picking && (
        <div className="owned-pick">
          <span>{loc.fake ? 'Which one is genuine?' : 'Which one is the fake?'}</span>
          {lines.map((line) => (
            <button
              key={line}
              className="btn"
              disabled={busy}
              onClick={() => {
                onToggleFake(line)
                setPicking(false)
              }}
            >
              {line}
            </button>
          ))}
          {lines.length < loc.quantity && (
            <button
              className="btn ghost"
              disabled={busy}
              onClick={() => {
                onToggleFake()
                setPicking(false)
              }}
            >
              Another (no position)
            </button>
          )}
          <button className="link small" onClick={() => setPicking(false)}>
            Cancel
          </button>
        </div>
      )}
      {moving && (
        <div className="owned-move">
          Move
          <input
            className="input"
            type="number"
            min={1}
            max={loc.quantity}
            value={qty}
            onChange={(e) => setQty(Math.max(1, Math.min(loc.quantity, Number(e.target.value) || 1)))}
            aria-label="Copies to move"
          />
          {mustPick && qty === 1 && (
            <select className="input" value={moveLine} onChange={(e) => setMoveLine(e.target.value)} aria-label="Which one">
              <option value="">any</option>
              {lines.map((line) => (
                <option key={line} value={line}>
                  {line}
                </option>
              ))}
            </select>
          )}
          to
          <select className="input" value={target} onChange={(e) => setTarget(e.target.value ? Number(e.target.value) : '')}>
            <option value="">choose…</option>
            {others.map((l) => (
              <option key={l.id} value={l.id}>
                {l.name}
              </option>
            ))}
          </select>
          <button
            className="btn primary"
            disabled={busy || target === ''}
            onClick={() => {
              if (target !== '') onMove(target, Math.min(qty, loc.quantity), qty === 1 && moveLine ? moveLine : undefined)
              setMoving(false)
            }}
          >
            Move
          </button>
        </div>
      )}
      <textarea
        className="input owned-note"
        placeholder={loc.fake ? 'Note (e.g. AliExpress, June)' : 'Note (e.g. page 12)'}
        value={notes}
        rows={Math.max(1, notes.split('\n').length)}
        maxLength={500}
        onChange={(e) => setNotes(e.target.value)}
        onBlur={() => notes !== loc.notes && onNote(notes)}
        aria-label="Note"
      />
    </li>
  )
}
