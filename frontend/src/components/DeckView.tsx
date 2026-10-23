import { DndContext, MouseSensor, TouchSensor, closestCenter, useSensor, useSensors, type DragEndEvent } from '@dnd-kit/core'
import { SortableContext, arrayMove, rectSortingStrategy, useSortable } from '@dnd-kit/sortable'
import { CSS } from '@dnd-kit/utilities'
import { useMemo, useState } from 'react'
import { colorClass } from '../lib/colors'
import type { CardSummary, Location } from '../lib/types'

/** Reglas de construcción de Dragon Ball Super Masters que se comprueban. */
const MAIN_MIN = 50
const MAIN_MAX = 60
const MAX_COPIES = 4
// Límites de keyword skills (los mismos textos que publica Bandai en su página de keyword skills).
const SKILL_LIMITS: { skill: string; max: number; scope: 'card' | 'deck'; label: string }[] = [
  { skill: 'Ultimate', max: 1, scope: 'card', label: 'Ultimate: máx. 1 copia' },
  { skill: 'Super Combo', max: 4, scope: 'deck', label: 'Super Combo: máx. 4 en el mazo' },
  { skill: 'Dragon Ball', max: 7, scope: 'deck', label: 'Dragon Ball: máx. 7 en total' },
]
const TYPE_LABELS: Record<string, string> = { BATTLE: 'Battle', EXTRA: 'Extra', UNISON: 'Unison' }
const COLOR_ORDER = ['Red', 'Blue', 'Green', 'Yellow', 'Black', 'White']

type Section = 'main' | 'z'
const sectionOf = (c: CardSummary): Section | 'leader' =>
  c.card_type === 'LEADER' ? 'leader' : c.card_type.startsWith('Z-') ? 'z' : 'main'
const copies = (c: CardSummary) => c.quantity ?? 0

interface Issue {
  level: 'error' | 'warn'
  text: string
}

interface Props {
  deck: Location
  cards: CardSummary[]
  loading: boolean
  onOpen: (id: number) => void
  /** Con «Mi orden»: ids de todas las cartas del mazo en el nuevo orden. */
  onReorder?: (ids: number[]) => void
}

/** Vista de un mazo: líder, estadísticas, comprobación de reglas y cartas por secciones. */
export default function DeckView({ deck, cards, loading, onOpen, onReorder }: Props) {
  const leaders = cards.filter((c) => sectionOf(c) === 'leader')
  const leader = leaders[0]
  const main = cards.filter((c) => sectionOf(c) === 'main')
  const zDeck = cards.filter((c) => sectionOf(c) === 'z')
  const [showFront, setShowFront] = useState(false)

  const stats = useMemo(() => {
    const total = main.reduce((n, c) => n + copies(c), 0)
    const curve = new Map<number, number>()
    const types = new Map<string, number>()
    const colors = new Map<string, number>()
    for (const c of main) {
      const n = copies(c)
      const cost = Math.min(c.energy ?? 0, 10)
      curve.set(cost, (curve.get(cost) ?? 0) + n)
      types.set(c.card_type, (types.get(c.card_type) ?? 0) + n)
      for (const col of c.colors) colors.set(col, (colors.get(col) ?? 0) + n)
    }
    const maxCost = Math.max(6, ...curve.keys())
    const bars = Array.from({ length: maxCost + 1 }, (_, cost) => ({ cost, n: curve.get(cost) ?? 0 }))
    const avg = total ? main.reduce((s, c) => s + (c.energy ?? 0) * copies(c), 0) / total : 0
    return { total, bars, peak: Math.max(1, ...bars.map((b) => b.n)), avg, types, colors }
  }, [main])

  const { issues, flagged } = useMemo(() => {
    const issues: Issue[] = []
    const flagged = new Map<number, string>()
    if (!leader) issues.push({ level: 'error', text: 'Falta la carta Líder' })
    if (stats.total < MAIN_MIN || stats.total > MAIN_MAX) {
      issues.push({ level: 'error', text: `Mazo principal: ${stats.total} cartas (deben ser ${MAIN_MIN}–${MAIN_MAX})` })
    }
    // Copias por número de carta (las distintas impresiones de una carta cuentan juntas).
    const byNumber = new Map<string, { n: number; ids: number[]; name: string }>()
    for (const c of [...main, ...zDeck]) {
      const e = byNumber.get(c.card_number) ?? { n: 0, ids: [], name: c.name }
      e.n += copies(c)
      e.ids.push(c.id)
      byNumber.set(c.card_number, e)
    }
    for (const [num, e] of byNumber) {
      if (e.n > MAX_COPIES) {
        issues.push({ level: 'error', text: `${num} ${e.name}: ${e.n} copias (máx. ${MAX_COPIES})` })
        e.ids.forEach((id) => flagged.set(id, `Más de ${MAX_COPIES} copias`))
      }
    }
    for (const c of [...main, ...zDeck]) {
      if (c.legality === 'banned') {
        issues.push({ level: 'error', text: `${c.card_number} ${c.name} está prohibida` })
        flagged.set(c.id, 'Prohibida')
      } else if (c.legality === 'limited' && (byNumber.get(c.card_number)?.n ?? 0) > 1) {
        issues.push({ level: 'error', text: `${c.card_number} ${c.name} está limitada a 1 copia` })
        flagged.set(c.id, 'Limitada a 1')
      }
    }
    for (const rule of SKILL_LIMITS) {
      const withSkill = [...main, ...zDeck].filter((c) => c.keyword_skills.includes(rule.skill))
      if (rule.scope === 'card') {
        for (const c of withSkill) {
          if (copies(c) > rule.max) {
            issues.push({ level: 'error', text: `${c.card_number} ${c.name}: ${rule.label}` })
            flagged.set(c.id, rule.label)
          }
        }
      } else {
        const n = withSkill.reduce((s, c) => s + copies(c), 0)
        if (n > rule.max) {
          issues.push({ level: 'error', text: `${rule.label} (tienes ${n})` })
          withSkill.forEach((c) => flagged.set(c.id, rule.label))
        }
      }
    }
    if (leaders.length > 1) issues.push({ level: 'warn', text: `Hay ${leaders.length} cartas Líder en el mazo` })
    return { issues, flagged }
  }, [main, zDeck, leader, leaders.length, stats.total])

  const reorderSection = (section: Section, ids: number[]) => {
    if (!onReorder) return
    const order = [
      ...leaders.map((c) => c.id),
      ...(section === 'main' ? ids : main.map((c) => c.id)),
      ...(section === 'z' ? ids : zDeck.map((c) => c.id)),
    ]
    onReorder(order)
  }

  const leaderImage = leader && (showFront || !leader.back_image_url ? leader.image_url : leader.back_image_url)
  const zTotal = zDeck.reduce((n, c) => n + copies(c), 0)

  return (
    <div className={`deck-view ${loading ? 'loading' : ''}`}>
      <section className="deck-hero">
        <div className="deck-leader">
          {leader ? (
            <button
              className="deck-leader-card"
              onClick={() => leader.back_image_url && setShowFront(!showFront)}
              title={leader.back_image_url ? 'Pulsa para girar la carta' : leader.name}
            >
              <img src={leaderImage} alt={`Líder: ${leader.name}`} referrerPolicy="no-referrer" />
              {leader.back_image_url && <span className="deck-flip">{showFront ? 'Cara normal' : 'Despertado'} ⟲</span>}
            </button>
          ) : (
            <div className="deck-leader-card empty">Sin líder</div>
          )}
          {leader && (
            <button className="link small" onClick={() => onOpen(leader.id)}>
              {leader.card_number} · ficha
            </button>
          )}
        </div>

        <div className="deck-summary">
          <p className="deck-eyebrow">Mazo</p>
          <h2 className="deck-title">{deck.name}</h2>
          {leader && <p className="deck-leader-name">{showFront || !leader.back_name ? leader.name : leader.back_name}</p>}
          <div className="deck-counts">
            <span className={`deck-count ${stats.total >= MAIN_MIN && stats.total <= MAIN_MAX ? 'ok' : 'bad'}`}>
              <strong>{stats.total}</strong>/{MAIN_MAX} mazo principal
            </span>
            <span className="deck-count">
              <strong>{zTotal}</strong> Z Deck
            </span>
            <span className="deck-count">
              <strong>{stats.avg.toFixed(1)}</strong> coste medio
            </span>
          </div>
          <div className={`deck-check ${issues.some((i) => i.level === 'error') ? 'bad' : 'ok'}`}>
            {issues.length === 0 ? (
              <span>✓ Cumple las reglas de construcción</span>
            ) : (
              <ul>
                {issues.map((i) => (
                  <li key={i.text} className={i.level}>
                    {i.text}
                  </li>
                ))}
              </ul>
            )}
          </div>
        </div>

        <div className="deck-stats">
          <figure className="deck-curve" aria-label="Curva de energía del mazo principal">
            <figcaption>Curva de energía</figcaption>
            <div className="deck-bars">
              {stats.bars.map((b) => (
                <div key={b.cost} className="deck-bar" title={`Coste ${b.cost}${b.cost === 10 ? '+' : ''}: ${b.n} cartas`}>
                  <span className="deck-bar-n">{b.n || ''}</span>
                  <span className="deck-bar-fill" style={{ height: `${(b.n / stats.peak) * 100}%` }} />
                  <span className="deck-bar-x">{b.cost === 10 ? '10+' : b.cost}</span>
                </div>
              ))}
            </div>
          </figure>
          <div className="deck-mix">
            <p className="deck-mix-title">Tipos</p>
            <div className="deck-chips">
              {[...stats.types].map(([t, n]) => (
                <span key={t} className="deck-chip">
                  {TYPE_LABELS[t] ?? t} <strong>{n}</strong>
                </span>
              ))}
            </div>
            <p className="deck-mix-title">Colores</p>
            <div className="deck-colorbar" aria-label="Reparto por colores">
              {[...stats.colors]
                .sort((a, b) => COLOR_ORDER.indexOf(a[0]) - COLOR_ORDER.indexOf(b[0]))
                .map(([col, n]) => (
                  <span key={col} className={`bg ${colorClass(col)}`} style={{ flexGrow: n }} title={`${col}: ${n}`} />
                ))}
            </div>
            <div className="deck-chips">
              {[...stats.colors].map(([col, n]) => (
                <span key={col} className="deck-chip">
                  <i className={`dot ${colorClass(col)}`} /> {col} <strong>{n}</strong>
                </span>
              ))}
            </div>
          </div>
        </div>
      </section>

      <DeckSection
        title="Mazo principal"
        count={stats.total}
        cards={main}
        flagged={flagged}
        onOpen={onOpen}
        onReorder={onReorder ? (ids) => reorderSection('main', ids) : undefined}
      />
      {zDeck.length > 0 && (
        <DeckSection
          title="Z Deck"
          count={zTotal}
          cards={zDeck}
          flagged={flagged}
          onOpen={onOpen}
          onReorder={onReorder ? (ids) => reorderSection('z', ids) : undefined}
        />
      )}
      {onReorder && <p className="reorder-hint">Arrastra las cartas para ordenarlas dentro de su sección (en el móvil, mantén pulsada una carta).</p>}
    </div>
  )
}

function DeckSection({
  title,
  count,
  cards,
  flagged,
  onOpen,
  onReorder,
}: {
  title: string
  count: number
  cards: CardSummary[]
  flagged: Map<number, string>
  onOpen: (id: number) => void
  onReorder?: (ids: number[]) => void
}) {
  const sensors = useSensors(
    useSensor(MouseSensor, { activationConstraint: { distance: 6 } }),
    useSensor(TouchSensor, { activationConstraint: { delay: 250, tolerance: 6 } }),
  )
  const ids = cards.map((c) => c.id)
  const grid = (
    <ul className="deck-grid">
      {cards.map((c) =>
        onReorder ? (
          <SortableDeckCard key={c.id} card={c} flag={flagged.get(c.id)} onOpen={onOpen} />
        ) : (
          <li key={c.id}>
            <DeckCard card={c} flag={flagged.get(c.id)} onOpen={onOpen} />
          </li>
        ),
      )}
    </ul>
  )
  return (
    <section className="deck-section">
      <h3>
        {title} <span>{count} cartas</span>
      </h3>
      {cards.length === 0 ? (
        <p className="muted small">Sin cartas.</p>
      ) : onReorder ? (
        <DndContext
          sensors={sensors}
          collisionDetection={closestCenter}
          onDragEnd={({ active, over }: DragEndEvent) => {
            if (over && active.id !== over.id) onReorder(arrayMove(ids, ids.indexOf(Number(active.id)), ids.indexOf(Number(over.id))))
          }}
        >
          <SortableContext items={ids} strategy={rectSortingStrategy}>
            {grid}
          </SortableContext>
        </DndContext>
      ) : (
        grid
      )}
    </section>
  )
}

function SortableDeckCard({ card, flag, onOpen }: { card: CardSummary; flag?: string; onOpen: (id: number) => void }) {
  const { listeners, setNodeRef, transform, transition, isDragging } = useSortable({ id: card.id })
  return (
    <li
      ref={setNodeRef}
      className={`sortable ${isDragging ? 'dragging' : ''}`}
      style={{ transform: CSS.Transform.toString(transform), transition }}
      {...listeners}
    >
      <DeckCard card={card} flag={flag} onOpen={onOpen} />
    </li>
  )
}

function DeckCard({ card, flag, onOpen }: { card: CardSummary; flag?: string; onOpen: (id: number) => void }) {
  const n = copies(card)
  return (
    <button className={`deck-card ${flag ? 'flagged' : ''}`} onClick={() => onOpen(card.id)} title={`${card.card_number} · ${card.name}`}>
      <img src={card.image_url} alt={card.name} loading="lazy" referrerPolicy="no-referrer" draggable={false} />
      <span className="deck-qty" aria-label={`${n} copias`}>
        {n}
      </span>
      {flag && <span className="deck-flag">{flag}</span>}
      <span className="deck-card-name">
        <small>{card.card_number}</small>
        {card.name}
      </span>
    </button>
  )
}
