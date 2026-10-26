import { useMemo, useState } from 'react'
import type { CardSummary, Location, OwnedLocation } from '../lib/types'
import { cardThumb } from '../lib/types'
import type { Spot } from './OwnedPanel'

interface Props {
  cards: CardSummary[]
  locations: Location[]
  /** Ubicación filtrada en Mi colección (origen por defecto al mover). */
  filterLocation: number | null
  /** Con false, las copias falsas no se muestran ni se mueven en bloque. */
  showFakes?: boolean
  loading: boolean
  busy: Set<number>
  onOpen: (id: number) => void
  onMove: (id: number, source: Spot, target: Spot, quantity: number) => Promise<void>
}

/** Copias (auténticas y falsas) de una carta en una ubicación. */
const copiesIn = (card: CardSummary, location: number, withFakes = true) =>
  (card.locations ?? []).filter((l) => l.id === location && (withFakes || !l.fake)).reduce((n, l) => n + l.quantity, 0)

const spotKey = (l: OwnedLocation) => `${l.id}:${l.fake ? 1 : 0}`
const spotLabel = (l: OwnedLocation) => (l.fake ? `${l.name} (falsas)` : l.name)

/** Mi colección en modo lista: una fila por carta con su reparto y controles para mover copias. */
export default function CollectionList({ cards, locations, filterLocation, showFakes = true, loading, busy, onOpen, onMove }: Props) {
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
  const movable = source == null ? [] : cards.filter((c) => selected.has(c.id) && copiesIn(c, source, showFakes) > 0)

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
        // Las falsas siguen siendo falsas en el destino. Con "1 copia", primero una auténtica.
        const rows = (card.locations ?? []).filter((l) => l.id === source && (showFakes || !l.fake)).sort((a, b) => Number(a.fake) - Number(b.fake))
        for (const row of bulkAll ? rows : rows.slice(0, 1)) {
          await onMove(card.id, { location: source, fake: row.fake }, { location: bulkTarget, fake: row.fake }, bulkAll ? row.quantity : 1)
        }
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
            key={`${card.id}:${(card.locations ?? []).map((l) => `${spotKey(l)}x${l.quantity}`).join(',')}`}
            card={card}
            locations={locations}
            preferredSource={filterLocation ?? defaultId}
            showFakes={showFakes}
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
  showFakes,
  checked,
  busy,
  onToggle,
  onOpen,
  onMove,
}: {
  card: CardSummary
  locations: Location[]
  preferredSource: number | null
  showFakes: boolean
  checked: boolean
  busy: boolean
  onToggle: () => void
  onOpen: () => void
  onMove: (source: Spot, target: Spot, quantity: number) => void
}) {
  const owned = (card.locations ?? []).filter((l) => showFakes || !l.fake)
  const initial =
    owned.find((l) => l.id === preferredSource && !l.fake) ??
    owned.find((l) => l.id === preferredSource) ??
    [...owned].sort((a, b) => b.quantity - a.quantity)[0]
  const [sourceKey, setSourceKey] = useState(initial ? spotKey(initial) : '')
  const src = owned.find((l) => spotKey(l) === sourceKey)
  const source: number | '' = src?.id ?? ''
  const [target, setTarget] = useState<number | ''>('')
  const have = src?.quantity ?? 0
  const [qty, setQty] = useState(have)
  const amount = Math.max(1, Math.min(qty || have, have))

  return (
    <li className={`list-row ${checked ? 'checked' : ''}`}>
      <input type="checkbox" checked={checked} onChange={onToggle} aria-label={`Seleccionar ${card.name}`} />
      <button className="list-card" onClick={onOpen} title="Ver ficha">
        <img src={cardThumb(card)} alt="" loading="lazy" referrerPolicy="no-referrer" />
        <span>
          <strong>{card.name}</strong>
          <small className="muted">
            {card.card_number} · {card.card_type}
          </small>
        </span>
      </button>
      <span className="list-total" title="Copias en total">
        ×{owned.reduce((n, l) => n + l.quantity, 0)}
      </span>
      <span className="list-locs">
        {owned.map((l) => (
          <span
            key={spotKey(l)}
            className={`loc-chip ${spotKey(l) === sourceKey ? 'on' : ''} ${l.fake ? 'fake' : ''}`}
            title={l.notes || undefined}
          >
            {l.name}
            {l.fake && <em> falsa</em>} <strong>{l.quantity}</strong>
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
          value={sourceKey}
          onChange={(e) => {
            setSourceKey(e.target.value)
            setQty(owned.find((l) => spotKey(l) === e.target.value)?.quantity ?? 0)
          }}
          aria-label="Origen"
        >
          {owned.map((l) => (
            <option key={spotKey(l)} value={spotKey(l)}>
              {spotLabel(l)}
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
            if (src && target !== '') onMove({ location: src.id, fake: src.fake }, { location: target, fake: src.fake }, amount)
            setTarget('')
          }}
        >
          Mover
        </button>
      </span>
    </li>
  )
}
