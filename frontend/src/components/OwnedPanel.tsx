import { useState } from 'react'
import type { CardSummary, Location, OwnedLocation } from '../lib/types'

export const KIND_LABELS: Record<string, string> = { deck: 'Mazo', binder: 'Archivador', storage: 'Almacén', other: 'Otro' }

interface Props {
  card: CardSummary
  locations: Location[]
  busy: boolean
  notice?: string | null
  onAdjust: (location: number, delta: number) => void
  onMove: (source: number, target: number, quantity: number) => void
  onNote: (location: number, notes: string) => void
}

/** Ficha de una carta de Mi colección: sus copias en cada ubicación, con − / +, mover y nota. */
export default function OwnedPanel({ card, locations, busy, notice, onAdjust, onMove, onNote }: Props) {
  const owned = card.locations ?? []
  const total = card.total_quantity ?? card.quantity ?? 0
  const free = locations.filter((l) => !owned.some((o) => o.id === l.id))
  const [addTo, setAddTo] = useState<number | ''>('')

  return (
    <section className="owned-panel" aria-label="Copias en tu colección">
      <header>
        En tu colección: <strong>×{total}</strong>
      </header>
      {notice && <p className="owned-notice">{notice}</p>}
      <ul>
        {owned.map((loc) => (
          <OwnedRow
            key={loc.id}
            loc={loc}
            others={locations.filter((l) => l.id !== loc.id)}
            busy={busy}
            onAdjust={(delta) => onAdjust(loc.id, delta)}
            onMove={(target, qty) => onMove(loc.id, target, qty)}
            onNote={(notes) => onNote(loc.id, notes)}
          />
        ))}
      </ul>
      {free.length > 0 && (
        <div className="owned-add">
          <span>Añadir una copia en</span>
          <select className="input" value={addTo} onChange={(e) => setAddTo(e.target.value ? Number(e.target.value) : '')}>
            <option value="">elige ubicación…</option>
            {free.map((l) => (
              <option key={l.id} value={l.id}>
                {l.name}
              </option>
            ))}
          </select>
          <button
            className="btn"
            disabled={busy || addTo === ''}
            onClick={() => {
              if (addTo !== '') onAdjust(addTo, 1)
              setAddTo('')
            }}
          >
            Añadir
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
  onNote,
}: {
  loc: OwnedLocation
  others: Location[]
  busy: boolean
  onAdjust: (delta: number) => void
  onMove: (target: number, quantity: number) => void
  onNote: (notes: string) => void
}) {
  const [moving, setMoving] = useState(false)
  const [target, setTarget] = useState<number | ''>('')
  const [qty, setQty] = useState(loc.quantity)
  const [notes, setNotes] = useState(loc.notes)

  return (
    <li>
      <div className="owned-row">
        <span className="owned-name">
          {loc.name}
          {loc.kind !== 'other' && <small>{KIND_LABELS[loc.kind]}</small>}
        </span>
        <span className="owned-qty">
          <button className="qty-btn" disabled={busy} onClick={() => onAdjust(-1)} aria-label={`Quitar una copia de ${loc.name}`}>
            −
          </button>
          <strong>{loc.quantity}</strong>
          <button className="qty-btn" disabled={busy} onClick={() => onAdjust(1)} aria-label={`Añadir una copia en ${loc.name}`}>
            +
          </button>
        </span>
        {others.length > 0 && (
          <button className="link small" onClick={() => setMoving(!moving)} aria-expanded={moving}>
            Mover…
          </button>
        )}
      </div>
      {moving && (
        <div className="owned-move">
          Mover
          <input
            className="input"
            type="number"
            min={1}
            max={loc.quantity}
            value={qty}
            onChange={(e) => setQty(Math.max(1, Math.min(loc.quantity, Number(e.target.value) || 1)))}
            aria-label="Copias a mover"
          />
          a
          <select className="input" value={target} onChange={(e) => setTarget(e.target.value ? Number(e.target.value) : '')}>
            <option value="">elige…</option>
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
              if (target !== '') onMove(target, Math.min(qty, loc.quantity))
              setMoving(false)
            }}
          >
            Mover
          </button>
        </div>
      )}
      <input
        className="input owned-note"
        placeholder="Nota (p. ej. página 12)"
        value={notes}
        maxLength={500}
        onChange={(e) => setNotes(e.target.value)}
        onBlur={() => notes !== loc.notes && onNote(notes)}
        onKeyDown={(e) => e.key === 'Enter' && e.currentTarget.blur()}
      />
    </li>
  )
}
