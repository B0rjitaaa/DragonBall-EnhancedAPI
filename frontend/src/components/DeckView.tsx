import { DndContext, MouseSensor, TouchSensor, closestCenter, useSensor, useSensors, type DragEndEvent } from '@dnd-kit/core'
import { SortableContext, arrayMove, rectSortingStrategy, useSortable } from '@dnd-kit/sortable'
import { CSS } from '@dnd-kit/utilities'
import { useCallback, useEffect, useMemo, useState } from 'react'
import { api } from '../lib/api'
import { colorClass } from '../lib/colors'
import type { CardSummary, DeckDetail, DeckVersionDetail, Location } from '../lib/types'
import { MatchesPanel, VersionBar, versionLabel } from './DeckHistory'

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

interface Filter {
  cost: number[]
  type: string[]
  color: string[]
}
const NO_FILTER: Filter = { cost: [], type: [], color: [] }

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

interface CardAction {
  label: string
  title: string
  run: (card: CardSummary) => void
}

/** Vista de un mazo: líder, estadísticas, comprobación de reglas, cartas por secciones, versiones y partidas. */
export default function DeckView({ deck, cards, loading, onOpen, onReorder }: Props) {
  const [detail, setDetail] = useState<DeckDetail | null>(null)
  const [selected, setSelected] = useState<number | null>(null)
  const [loadedVersion, setLoadedVersion] = useState<DeckVersionDetail | null>(null)
  const version = selected != null && loadedVersion?.id === selected ? loadedVersion : null
  const [sideBusy, setSideBusy] = useState(false)
  const [historyError, setHistoryError] = useState('')

  const reload = useCallback(() => {
    api
      .deck(deck.id)
      .then((d) => {
        setDetail(d)
        setHistoryError('')
      })
      .catch((e) => setHistoryError((e as Error).message))
  }, [deck.id])
  // Las copias del mazo pueden cambiar desde fuera (escáner, mover copias): se recarga con las cartas.
  useEffect(reload, [reload, cards])
  useEffect(() => {
    if (selected == null) return
    let alive = true
    api.deckVersion(selected).then((v) => alive && setLoadedVersion(v)).catch(() => alive && setSelected(null))
    return () => {
      alive = false
    }
  }, [selected, detail])

  // Cartas a mostrar: la lista principal (las copias del mazo menos las del side) o la de la versión elegida.
  const { pool, side } = useMemo(() => {
    if (selected != null) {
      if (!version) return { pool: [] as CardSummary[], side: [] as CardSummary[] }
      const of = (section: string) =>
        version.cards
          .filter((c) => (section === 'side' ? c.section === 'side' : c.section !== 'side') && version.catalog[c.bandai_id])
          .map((c) => ({ ...version.catalog[c.bandai_id], quantity: c.quantity }))
      return { pool: of('main'), side: of('side') }
    }
    const sideQty = new Map((detail?.current ?? []).filter((c) => c.section === 'side').map((c) => [c.bandai_id, c.quantity]))
    return {
      pool: cards
        .map((c) => ({ ...c, quantity: Math.max(0, copies(c) - (sideQty.get(c.id) ?? 0)) }))
        .filter((c) => c.quantity > 0),
      side: cards.filter((c) => sideQty.has(c.id)).map((c) => ({ ...c, quantity: Math.min(copies(c), sideQty.get(c.id)!) })),
    }
  }, [selected, version, detail, cards])

  const leaders = pool.filter((c) => sectionOf(c) === 'leader')
  const leader = leaders[0]
  const main = pool.filter((c) => sectionOf(c) === 'main')
  const zDeck = pool.filter((c) => sectionOf(c) === 'z')
  const [showFront, setShowFront] = useState(false)
  const viewingCurrent = selected == null
  const sideOf = (id: number) => side.find((c) => c.id === id)?.quantity ?? 0

  const moveSide = async (card: CardSummary, delta: number) => {
    setSideBusy(true)
    try {
      await api.setSide(deck.id, card.id, sideOf(card.id) + delta)
      reload()
    } catch (e) {
      window.alert((e as Error).message)
    } finally {
      setSideBusy(false)
    }
  }
  const toSide: CardAction | undefined =
    viewingCurrent && !sideBusy ? { label: '→ Side', title: 'Pasar una copia al side deck', run: (c) => moveSide(c, 1) } : undefined
  const fromSide: CardAction | undefined =
    viewingCurrent && !sideBusy ? { label: '↩ Mazo', title: 'Devolver una copia al mazo', run: (c) => moveSide(c, -1) } : undefined
  const canReorderNow = viewingCurrent && onReorder

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
    if (stats.total < MAIN_MIN) {
      const n = MAIN_MIN - stats.total
      issues.push({ level: 'error', text: `Faltan ${n} ${n === 1 ? 'carta' : 'cartas'} para llegar a ${MAIN_MIN}` })
    } else if (stats.total > MAIN_MAX) {
      const n = stats.total - MAIN_MAX
      issues.push({ level: 'error', text: `Sobran ${n} ${n === 1 ? 'carta' : 'cartas'} (máximo ${MAIN_MAX})` })
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

  // Filtros desde las estadísticas (coste, tipo, color): se aplican a cada sección por separado.
  const [filter, setFilter] = useState<Filter>(NO_FILTER)
  const filtering = filter.cost.length + filter.type.length + filter.color.length > 0
  const toggle = <K extends keyof Filter>(key: K, value: Filter[K][number]) =>
    setFilter((f) => {
      const list = f[key] as Filter[K][number][]
      return { ...f, [key]: list.includes(value) ? list.filter((v) => v !== value) : [...list, value] }
    })
  const passes = (c: CardSummary) =>
    (!filter.cost.length || filter.cost.includes(Math.min(c.energy ?? 0, 10))) &&
    (!filter.type.length || filter.type.includes(c.card_type)) &&
    (!filter.color.length || c.colors.some((col) => filter.color.includes(col)))
  const shown = (list: CardSummary[]) => (filtering ? list.filter(passes) : list)
  const countOf = (list: CardSummary[]) => list.reduce((n, c) => n + copies(c), 0)
  const onClass = (on: boolean) => (on ? 'on' : filtering ? 'dim' : '')

  const reorderSection = (section: Section, ids: number[]) => {
    if (!onReorder) return
    const order = [
      ...leaders.map((c) => c.id),
      ...(section === 'main' ? ids : main.map((c) => c.id)),
      ...(section === 'z' ? ids : zDeck.map((c) => c.id)),
    ]
    onReorder([...order, ...side.map((c) => c.id).filter((id) => !order.includes(id))])
  }

  const leaderImage = leader && (showFront || !leader.back_image_url ? leader.image_url : leader.back_image_url)
  const zTotal = zDeck.reduce((n, c) => n + copies(c), 0)
  const sideTotal = side.reduce((n, c) => n + copies(c), 0)

  const catalog = { ...(detail?.catalog ?? {}), ...(version?.catalog ?? {}) }

  return (
    <div className={`deck-view ${loading || (selected != null && !version) ? 'loading' : ''}`}>
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
          <p className="deck-eyebrow">Mazo{version ? ` · ${versionLabel(version)}` : ''}</p>
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
            {sideTotal > 0 && (
              <span className="deck-count">
                <strong>{sideTotal}</strong> side
              </span>
            )}
          </div>
          {issues.length === 0 ? (
            <span className="deck-check ok">✓ Cumple las reglas de construcción</span>
          ) : issues.length === 1 ? (
            <span className={`deck-check ${issues[0].level}`}>⚠ {issues[0].text}</span>
          ) : (
            <details className={`deck-check ${issues.some((i) => i.level === 'error') ? 'error' : 'warn'}`}>
              <summary>⚠ {issues.length} avisos de construcción</summary>
              <ul>
                {issues.map((i) => (
                  <li key={i.text}>{i.text}</li>
                ))}
              </ul>
            </details>
          )}
        </div>

        {detail ? (
          <MatchesPanel
            deckId={deck.id}
            matches={version ? version.matches.map((m) => ({ ...m, version_number: version.number })) : detail.matches}
            record={version?.record ?? detail.record}
            byLeader={version?.by_leader ?? detail.by_leader}
            catalog={catalog}
            version={version}
            onChanged={reload}
          />
        ) : (
          <div className="deck-record" />
        )}

        <div className="deck-stats">
          <figure className="deck-curve" aria-label="Curva de energía del mazo principal">
            <figcaption>Curva de energía</figcaption>
            <div className="deck-bars">
              {stats.bars.map((b) => (
                <button
                  key={b.cost}
                  className={`deck-bar ${onClass(filter.cost.includes(b.cost))}`}
                  title={`Coste ${b.cost}${b.cost === 10 ? '+' : ''}: ${b.n} cartas · pulsa para filtrar`}
                  aria-pressed={filter.cost.includes(b.cost)}
                  onClick={() => toggle('cost', b.cost)}
                >
                  <span className="deck-bar-n">{b.n || ''}</span>
                  <span className="deck-bar-fill" style={{ height: `${(b.n / stats.peak) * 100}%` }} />
                  <span className="deck-bar-x">{b.cost === 10 ? '10+' : b.cost}</span>
                </button>
              ))}
            </div>
          </figure>
          <div className="deck-mix">
            <p className="deck-mix-title">Tipos</p>
            <div className="deck-chips">
              {[...stats.types].map(([t, n]) => (
                <button
                  key={t}
                  className={`deck-chip ${onClass(filter.type.includes(t))}`}
                  aria-pressed={filter.type.includes(t)}
                  onClick={() => toggle('type', t)}
                >
                  {TYPE_LABELS[t] ?? t} <strong>{n}</strong>
                </button>
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
                <button
                  key={col}
                  className={`deck-chip ${onClass(filter.color.includes(col))}`}
                  aria-pressed={filter.color.includes(col)}
                  onClick={() => toggle('color', col)}
                >
                  <i className={`dot ${colorClass(col)}`} /> {col} <strong>{n}</strong>
                </button>
              ))}
            </div>
            {filtering && (
              <button className="link small deck-filter-clear" onClick={() => setFilter(NO_FILTER)}>
                ✕ Quitar filtros
              </button>
            )}
          </div>
        </div>
      </section>

      {detail ? (
        <VersionBar detail={detail} selected={selected} version={version} onSelect={setSelected} onChanged={reload} />
      ) : historyError ? (
        <p className="muted small">No se pudieron cargar las versiones del mazo: {historyError}</p>
      ) : null}

      <DeckSection
        title="Mazo principal"
        count={stats.total}
        shown={filtering ? countOf(shown(main)) : undefined}
        cards={shown(main)}
        flagged={flagged}
        onOpen={onOpen}
        action={toSide}
        onReorder={canReorderNow && !filtering ? (ids) => reorderSection('main', ids) : undefined}
      />
      {zDeck.length > 0 && (
        <DeckSection
          title="Z Deck"
          count={zTotal}
          shown={filtering ? countOf(shown(zDeck)) : undefined}
          cards={shown(zDeck)}
          flagged={flagged}
          onOpen={onOpen}
          action={toSide}
          onReorder={canReorderNow && !filtering ? (ids) => reorderSection('z', ids) : undefined}
        />
      )}
      {(side.length > 0 || viewingCurrent) && (
        <DeckSection
          title="Side deck"
          count={sideTotal}
          shown={filtering ? countOf(shown(side)) : undefined}
          cards={shown(side)}
          flagged={new Map()}
          onOpen={onOpen}
          action={fromSide}
          empty={
            filtering
              ? 'Ninguna carta del side con estos filtros.'
              : viewingCurrent
                ? 'Sin cartas en el side. Usa «→ Side» en una carta del mazo para apartar copias.'
                : undefined
          }
        />
      )}
      {canReorderNow && !filtering && <p className="reorder-hint">Arrastra las cartas para ordenarlas dentro de su sección (en el móvil, mantén pulsada una carta).</p>}

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
  action,
  shown,
  empty = shown != null ? 'Ninguna carta con estos filtros.' : 'Sin cartas.',
}: {
  title: string
  count: number
  /** Con filtros: copias que se ven. */
  shown?: number
  cards: CardSummary[]
  flagged: Map<number, string>
  onOpen: (id: number) => void
  onReorder?: (ids: number[]) => void
  action?: CardAction
  empty?: string
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
          <SortableDeckCard key={c.id} card={c} flag={flagged.get(c.id)} onOpen={onOpen} action={action} />
        ) : (
          <li key={c.id}>
            <DeckCard card={c} flag={flagged.get(c.id)} onOpen={onOpen} action={action} />
          </li>
        ),
      )}
    </ul>
  )
  return (
    <section className="deck-section">
      <h3>
        {title} <span>{shown != null ? `${shown} de ${count}` : count} cartas</span>
      </h3>
      {cards.length === 0 ? (
        <p className="muted small">{empty}</p>
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

function SortableDeckCard({
  card,
  flag,
  onOpen,
  action,
}: {
  card: CardSummary
  flag?: string
  onOpen: (id: number) => void
  action?: CardAction
}) {
  const { listeners, setNodeRef, transform, transition, isDragging } = useSortable({ id: card.id })
  return (
    <li
      ref={setNodeRef}
      className={`sortable ${isDragging ? 'dragging' : ''}`}
      style={{ transform: CSS.Transform.toString(transform), transition }}
      {...listeners}
    >
      <DeckCard card={card} flag={flag} onOpen={onOpen} action={action} />
    </li>
  )
}

function DeckCard({
  card,
  flag,
  onOpen,
  action,
}: {
  card: CardSummary
  flag?: string
  onOpen: (id: number) => void
  action?: CardAction
}) {
  const n = copies(card)
  return (
    <div className="deck-card-wrap">
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
    {action && (
      <button
        className="deck-card-action"
        title={action.title}
        onPointerDown={(e) => e.stopPropagation()}
        onClick={() => action.run(card)}
      >
        {action.label}
      </button>
    )}
    </div>
  )
}
