import { useMemo, useState } from 'react'
import type { CardSummary, Location } from '../lib/types'

interface Props {
  cards: CardSummary[]
  locations: Location[]
  /** Ubicación filtrada en Mi colección (origen por defecto al mover). */
  filterLocation: number | null
  loading: boolean
  busy: Set<number>
  onOpen: (id: number) => void
  onMove: (id: number, source: number, target: number, quantity: number) => Promise<void>
}

const copiesIn = (card: CardSummary, location: number) =>
  card.locations?.find((l) => l.id === location)?.quantity ?? 0

/** Mi colección en modo lista: una fila por carta con su reparto y controles para mover copias. */
export default function CollectionList({ cards, locations, filterLocation, loading, busy, onOpen, onMove }: Props) {
  const defaultId = locations.find((l) => l.is_default)?.id ?? null
  const [selected, setSelected] = useState<Set<number>>(() => new Set())
  const [bulkSource, setBulkSource] = useState<number | ''>(filterLocation ?? defaultId ?? '')
  const [bulkTarget, setBulkTarget] = useState<number | ''>('')
  const [bulkAll, setBulkAll] = useState(true)
  const [bulkBusy, setBulkBusy] = useState(false)

  const visible = useMemo(() => new Set(cards.map((c) => c.id)), [cards])
  const chosen = [...selected].filter((id) => visible.has(id))
  const allChecked = cards.length > 0 && cards.every((c) => selected.has(c.id))
  const source = bulkSource === '' ? null : bulkSource
  const movable = source == null ? [] : cards.filter((c) => selected.has(c.id) && copiesIn(c, source) > 0)

  const toggle = (id: number) =>
    setSelected((s) => {
      const next = new Set(s)
      if (next.has(id)) next.delete(id)
      else next.add(id)
      return next
    })

  const bulkMove = async () => {
    if (source == null || bulkTarget === '') return
    setBulkBusy(true)
    try {
      for (const card of movable) {
        const have = copiesIn(card, source)
        await onMove(card.id, source, bulkTarget, bulkAll ? have : 1)
      }
      setSelected(new Set())
    } finally {
      setBulkBusy(false)
    }
  }

  if (!loading && cards.length === 0) return <div className="empty">No hay cartas que cumplan estos filtros.</div>

  return (
    <div className={`collection-list ${loading ? 'loading' : ''}`}>
      <div className={`bulk-bar ${chosen.length ? 'active' : ''}`}>
        <label className="bulk-check">
          <input
            type="checkbox"
            checked={allChecked}
            onChange={() => setSelected(allChecked ? new Set() : new Set(cards.map((c) => c.id)))}
            aria-label="Seleccionar todas las de esta página"
          />
          {chosen.length ? `${chosen.length} seleccionadas` : 'Seleccionar todas'}
        </label>
        {chosen.length > 0 && (
          <span className="bulk-move">
            Mover
            <select className="input" value={bulkAll ? 'all' : 'one'} onChange={(e) => setBulkAll(e.target.value === 'all')}>
              <option value="all">todas sus copias</option>
              <option value="one">1 copia</option>
            </select>
            de
            <select className="input" value={bulkSource} onChange={(e) => setBulkSource(e.target.value ? Number(e.target.value) : '')}>
              {locations.map((l) => (
                <option key={l.id} value={l.id}>
                  {l.name}
                </option>
              ))}
            </select>
            a
            <select className="input" value={bulkTarget} onChange={(e) => setBulkTarget(e.target.value ? Number(e.target.value) : '')}>
              <option value="">elige destino…</option>
              {locations
                .filter((l) => l.id !== source)
                .map((l) => (
                  <option key={l.id} value={l.id}>
                    {l.name}
                  </option>
                ))}
            </select>
            <button
              className="btn primary"
              disabled={bulkBusy || bulkTarget === '' || movable.length === 0}
              onClick={() => void bulkMove()}
              title={movable.length < chosen.length ? `${chosen.length - movable.length} no tienen copias en el origen` : undefined}
            >
              {bulkBusy ? 'Moviendo…' : `Mover ${movable.length}`}
            </button>
            <button className="link small" onClick={() => setSelected(new Set())}>
              Quitar selección
            </button>
          </span>
        )}
      </div>

      <ul className="list-rows">
        {cards.map((card) => (
          <ListRow
            // Con cada cambio en su reparto, la fila se reinicia (origen y copias a mover).
            key={`${card.id}:${(card.locations ?? []).map((l) => `${l.id}x${l.quantity}`).join(',')}`}
            card={card}
            locations={locations}
            preferredSource={filterLocation ?? defaultId}
            checked={selected.has(card.id)}
            busy={busy.has(card.id) || bulkBusy}
            onToggle={() => toggle(card.id)}
            onOpen={() => onOpen(card.id)}
            onMove={(src, tgt, qty) => void onMove(card.id, src, tgt, qty)}
          />
        ))}
      </ul>
    </div>
  )
}

function ListRow({
  card,
  locations,
  preferredSource,
  checked,
  busy,
  onToggle,
  onOpen,
  onMove,
}: {
  card: CardSummary
  locations: Location[]
  preferredSource: number | null
  checked: boolean
  busy: boolean
  onToggle: () => void
  onOpen: () => void
  onMove: (source: number, target: number, quantity: number) => void
}) {
  const owned = card.locations ?? []
  const initialSource =
    owned.find((l) => l.id === preferredSource)?.id ?? [...owned].sort((a, b) => b.quantity - a.quantity)[0]?.id ?? ''
  const [source, setSource] = useState<number | ''>(initialSource)
  const [target, setTarget] = useState<number | ''>('')
  const have = source === '' ? 0 : copiesIn(card, source)
  const [qty, setQty] = useState(have)
  const amount = Math.max(1, Math.min(qty || have, have))

  return (
    <li className={`list-row ${checked ? 'checked' : ''}`}>
      <input type="checkbox" checked={checked} onChange={onToggle} aria-label={`Seleccionar ${card.name}`} />
      <button className="list-card" onClick={onOpen} title="Ver ficha">
        <img src={card.image_url} alt="" loading="lazy" referrerPolicy="no-referrer" />
        <span>
          <strong>{card.name}</strong>
          <small className="muted">
            {card.card_number} · {card.card_type}
          </small>
        </span>
      </button>
      <span className="list-total" title="Copias en total">
        ×{card.total_quantity ?? card.quantity}
      </span>
      <span className="list-locs">
        {owned.map((l) => (
          <span key={l.id} className={`loc-chip ${l.id === source ? 'on' : ''}`} title={l.notes || undefined}>
            {l.name} <strong>{l.quantity}</strong>
          </span>
        ))}
      </span>
      <span className="list-move">
        <input
          className="input"
          type="number"
          min={1}
          max={have}
          value={amount}
          onChange={(e) => setQty(Number(e.target.value))}
          aria-label="Copias a mover"
          disabled={!have}
        />
        de
        <select
          className="input"
          value={source}
          onChange={(e) => {
            const id = e.target.value ? Number(e.target.value) : ''
            setSource(id)
            setQty(id === '' ? 0 : copiesIn(card, id))
          }}
          aria-label="Origen"
        >
          {owned.map((l) => (
            <option key={l.id} value={l.id}>
              {l.name}
            </option>
          ))}
        </select>
        a
        <select
          className="input"
          value={target}
          onChange={(e) => setTarget(e.target.value ? Number(e.target.value) : '')}
          aria-label="Destino"
        >
          <option value="">destino…</option>
          {locations
            .filter((l) => l.id !== source)
            .map((l) => (
              <option key={l.id} value={l.id}>
                {l.name}
              </option>
            ))}
        </select>
        <button
          className="btn"
          disabled={busy || source === '' || target === '' || !have}
          onClick={() => {
            if (source !== '' && target !== '') onMove(source, target, amount)
            setTarget('')
          }}
        >
          Mover
        </button>
      </span>
    </li>
  )
}
