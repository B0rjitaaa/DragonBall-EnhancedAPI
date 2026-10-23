import { useState } from 'react'
import type { CardSummary, Location, OwnedLocation } from '../lib/types'

export const KIND_LABELS: Record<string, string> = { deck: 'Mazo', binder: 'Archivador', storage: 'Almacén', other: 'Otro' }

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

/** Ficha de una carta de Mi colección: sus copias en cada ubicación, con − / +, mover, falsas y nota. */
export default function OwnedPanel({ card, locations, busy, notice, onAdjust, onMove, onNote }: Props) {
  const owned = card.locations ?? []
  const total = card.total_quantity ?? card.quantity ?? 0
  const fakes = card.fakes ?? owned.filter((l) => l.fake).reduce((n, l) => n + l.quantity, 0)
  const free = locations.filter((l) => !owned.some((o) => o.id === l.id && !o.fake))
  const [addTo, setAddTo] = useState<number | ''>('')

  return (
    <section className="owned-panel" aria-label="Copias en tu colección">
      <header>
        En tu colección: <strong>×{total}</strong>
        {fakes > 0 && <span className="fake-badge">{fakes === 1 ? '1 falsa' : `${fakes} falsas`}</span>}
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
              if (addTo !== '') onAdjust({ location: addTo, fake: false }, 1)
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
          {loc.kind !== 'other' && <small>{KIND_LABELS[loc.kind]}</small>}
          {loc.fake && <span className="fake-badge">Falsa</span>}
        </span>
        <span className="owned-qty">
          <button className="qty-btn" disabled={busy} onClick={() => onAdjust(-1)} aria-label={`Quitar una copia${loc.fake ? ' falsa' : ''} de ${loc.name}`}>
            −
          </button>
          <strong>{loc.quantity}</strong>
          {/* Las copias nuevas son auténticas: en una fila de falsas, + no tiene sentido. */}
          {!loc.fake && (
            <button className="qty-btn" disabled={busy} onClick={() => onAdjust(1)} aria-label={`Añadir una copia en ${loc.name}`}>
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
            title={loc.fake ? 'Una de estas copias es auténtica' : 'Una de estas copias es falsa'}
          >
            {loc.fake ? 'Es auténtica' : 'Marcar falsa'}
          </button>
          {others.length > 0 && (
            <button className="link small" onClick={() => setMoving(!moving)} aria-expanded={moving}>
              Mover…
            </button>
          )}
        </span>
      </div>
      {picking && (
        <div className="owned-pick">
          <span>{loc.fake ? '¿Cuál es auténtica?' : '¿Cuál es la falsa?'}</span>
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
              Otra (sin posición)
            </button>
          )}
          <button className="link small" onClick={() => setPicking(false)}>
            Cancelar
          </button>
        </div>
      )}
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
          {mustPick && qty === 1 && (
            <select className="input" value={moveLine} onChange={(e) => setMoveLine(e.target.value)} aria-label="Cuál">
              <option value="">cualquiera</option>
              {lines.map((line) => (
                <option key={line} value={line}>
                  {line}
                </option>
              ))}
            </select>
          )}
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
              if (target !== '') onMove(target, Math.min(qty, loc.quantity), qty === 1 && moveLine ? moveLine : undefined)
              setMoving(false)
            }}
          >
            Mover
          </button>
        </div>
      )}
      <textarea
        className="input owned-note"
        placeholder={loc.fake ? 'Nota (p. ej. AliExpress, junio)' : 'Nota (p. ej. página 12)'}
        value={notes}
        rows={Math.max(1, notes.split('\n').length)}
        maxLength={500}
        onChange={(e) => setNotes(e.target.value)}
        onBlur={() => notes !== loc.notes && onNote(notes)}
        aria-label="Nota"
      />
    </li>
  )
}
