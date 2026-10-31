import { DndContext, MouseSensor, TouchSensor, closestCenter, useSensor, useSensors, type DragEndEvent } from '@dnd-kit/core'
import { SortableContext, arrayMove, rectSortingStrategy, useSortable } from '@dnd-kit/sortable'
import { CSS } from '@dnd-kit/utilities'
import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { api } from '../lib/api'
import { colorClass } from '../lib/colors'
import type { CardSummary, DeckChange, DeckDetail, DeckListCard, DeckVersionDetail, Location, RestoreResult } from '../lib/types'
import { deckListText, isExportable, timeChamberUrl, type ExportDeck } from '../lib/deckExport'
import { cardThumb } from '../lib/types'
import { CardPicker, MatchesPanel, SaveListModal, VersionBar, versionLabel } from './DeckHistory'
import { PickListDialog } from './PickList'

/** Reglas de construcción de Dragon Ball Super Masters que se comprueban. */
const MAIN_MIN = 50
const MAIN_MAX = 60
const MAX_COPIES = 4
// Límites de keyword skills (los mismos textos que publica Bandai en su página de keyword skills).
const SKILL_LIMITS: { skill: string; max: number; scope: 'card' | 'deck'; label: string }[] = [
  { skill: 'Ultimate', max: 1, scope: 'card', label: 'Ultimate: 1 copy max' },
  { skill: 'Super Combo', max: 4, scope: 'deck', label: 'Super Combo: 4 max in the deck' },
  { skill: 'Dragon Ball', max: 7, scope: 'deck', label: 'Dragon Ball: 7 max in total' },
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
  /** Se han movido copias desde la vista del mazo (hacer principal una versión). */
  onCollectionChanged?: () => void
}

/** Controles de cada carta en la lista principal (que se está editando). */
interface CardControls {
  change: (card: CardSummary, delta: number) => void
  /** Pasar una copia al side (o devolverla al mazo). */
  move: { label: string; title: string; run: (card: CardSummary) => void }
  /** Diferencia con lo que hay en la caja, para marcar lo cambiado. */
  deltaOf: (card: CardSummary) => number
}

/** Borrador de la lista principal: copias por carta, en el mazo (main/Z/líder, según su tipo) o en el side. */
type Part = 'deck' | 'side'
type Draft = Record<string, number>
const draftKey = (id: number, part: Part) => `${id}:${part}`
const storageKey = (deckId: number) => `deck-draft:${deckId}`

/** `order`: el orden arrastrado mientras se edita (incluye las cartas añadidas, que aún no están en la caja). */
interface DraftState {
  draft: Draft
  added: Record<number, CardSummary>
  order: number[]
}

function loadDraft(deckId: number): DraftState {
  try {
    const raw = window.localStorage.getItem(storageKey(deckId))
    if (raw) return { order: [], ...JSON.parse(raw) }
  } catch {
    /* sin almacenamiento: el borrador solo vive en esta pestaña */
  }
  return { draft: {}, added: {}, order: [] }
}

function saveDraft(deckId: number, { draft, added, order }: DraftState) {
  try {
    if (Object.keys(draft).length) window.localStorage.setItem(storageKey(deckId), JSON.stringify({ draft, added, order }))
    else window.localStorage.removeItem(storageKey(deckId))
  } catch {
    /* sin almacenamiento */
  }
}

/** Vista de un mazo: líder, estadísticas, comprobación de reglas, cartas por secciones, listas y partidas. */
export default function DeckView({ deck, cards, loading, onOpen, onReorder, onCollectionChanged }: Props) {
  const [detail, setDetail] = useState<DeckDetail | null>(null)
  const [selected, setSelected] = useState<number | null>(null)
  const [loadedVersion, setLoadedVersion] = useState<DeckVersionDetail | null>(null)
  const version = selected != null && loadedVersion?.id === selected ? loadedVersion : null
  const [historyError, setHistoryError] = useState('')
  const [restored, setRestored] = useState<RestoreResult | null>(null)
  const [picking, setPicking] = useState(false)
  const [saving, setSaving] = useState(false)
  // Lo editado en la lista principal (copias absolutas por carta y parte) y las cartas añadidas desde el catálogo.
  const [{ draft, added, order: draftOrder }, setDraftState] = useState(() => loadDraft(deck.id))
  useEffect(() => saveDraft(deck.id, { draft, added, order: draftOrder }), [deck.id, draft, added, draftOrder])

  const reload = useCallback(() => {
    api
      .deck(deck.id)
      .then((d) => {
        setDetail(d)
        setHistoryError('')
      })
      .catch((e) => setHistoryError((e as Error).message))
  }, [deck.id])
  // Las copias del mazo pueden cambiar desde fuera (escáner, mover copias): se recarga cuando
  // cambian de verdad (no cada vez que se redibuja la lista, que crea otro array con lo mismo).
  const copiesKey = useMemo(() => cards.map((c) => `${c.id}:${c.quantity ?? 0}`).join(','), [cards])
  const lastKey = useRef('')
  useEffect(reload, [reload])
  useEffect(() => {
    // La primera llegada de las cartas (lista vacía → llena) no es un cambio de copias.
    if (lastKey.current && copiesKey && copiesKey !== lastKey.current) reload()
    if (copiesKey) lastKey.current = copiesKey
  }, [copiesKey, reload])
  useEffect(() => {
    if (selected == null) return
    let alive = true
    api.deckVersion(selected).then((v) => alive && setLoadedVersion(v)).catch(() => alive && setSelected(null))
    return () => {
      alive = false
    }
  }, [selected, detail])

  // Datos de cada carta: las del mazo, las que salen en las listas y las añadidas a mano.
  const known = useMemo(() => {
    const map: Record<number, CardSummary> = { ...(detail?.catalog ?? {}), ...added }
    for (const c of cards) map[c.id] = c
    return map
  }, [detail, added, cards])

  // Lo que hay en la caja ahora, por carta y parte.
  const base = useMemo(() => {
    const b: Draft = {}
    for (const c of detail?.current ?? []) {
      const k = draftKey(c.bandai_id, c.section === 'side' ? 'side' : 'deck')
      b[k] = (b[k] ?? 0) + c.quantity
    }
    return b
  }, [detail])
  const listing = useMemo(() => {
    const l: Draft = { ...base, ...draft }
    for (const k of Object.keys(l)) if (!l[k]) delete l[k]
    return l
  }, [base, draft])
  const draftChanges: DeckChange[] = useMemo(
    () =>
      [...new Set([...Object.keys(base), ...Object.keys(listing)])]
        .map((k) => {
          const [id, part] = k.split(':')
          const card = known[Number(id)]
          const section: DeckChange['section'] =
            part === 'side' ? 'side' : card?.card_type.startsWith('Z-') ? 'z' : 'main'
          return { bandai_id: Number(id), section, delta: (listing[k] ?? 0) - (base[k] ?? 0) }
        })
        .filter((c) => c.delta !== 0),
    [base, listing, known],
  )
  const dirty = draftChanges.length > 0

  const setQty = (id: number, part: Part, n: number) =>
    setDraftState((st) => ({ ...st, draft: { ...st.draft, [draftKey(id, part)]: Math.max(0, Math.min(99, n)) } }))
  const qtyOf = (id: number, part: Part) => listing[draftKey(id, part)] ?? 0
  const discard = () => setDraftState({ draft: {}, added: {}, order: [] })
  const addCard = (card: CardSummary) => {
    setDraftState((st) => ({
      ...st,
      added: { ...st.added, [card.id]: card },
      draft: { ...st.draft, [draftKey(card.id, 'deck')]: (listing[draftKey(card.id, 'deck')] ?? 0) + 1 },
    }))
  }

  // Cartas a mostrar: la lista principal (con lo editado) o la de la lista elegida.
  const { pool, side } = useMemo(() => {
    if (selected != null) {
      if (!version) return { pool: [] as CardSummary[], side: [] as CardSummary[] }
      const of = (section: string) =>
        version.cards
          .filter((c) => (section === 'side' ? c.section === 'side' : c.section !== 'side') && version.catalog[c.bandai_id])
          .map((c) => ({ ...version.catalog[c.bandai_id], quantity: c.quantity }))
      return { pool: of('main'), side: of('side') }
    }
    // En el orden de la caja («Mi orden»); lo añadido, al final.
    const order = [...draftOrder, ...cards.map((c) => c.id), ...Object.keys(listing).map((k) => Number(k.split(':')[0]))]
    const ids = [...new Set(order)].filter((id) => known[id])
    const of = (part: Part) =>
      ids.filter((id) => listing[draftKey(id, part)]).map((id) => ({ ...known[id], quantity: listing[draftKey(id, part)] }))
    return { pool: of('deck'), side: of('side') }
  }, [selected, version, cards, listing, known, draftOrder])

  const leaders = pool.filter((c) => sectionOf(c) === 'leader')
  const leader = leaders[0]
  const main = pool.filter((c) => sectionOf(c) === 'main')
  const zDeck = pool.filter((c) => sectionOf(c) === 'z')
  const [showFront, setShowFront] = useState(false)
  const [showPicks, setShowPicks] = useState(false)
  const viewingCurrent = selected == null

  const deckControls: CardControls | undefined = viewingCurrent
    ? {
        change: (c, d) => setQty(c.id, 'deck', qtyOf(c.id, 'deck') + d),
        move: {
          label: '→ Side',
          title: 'Move a copy to the side deck',
          run: (c) => {
            setQty(c.id, 'deck', qtyOf(c.id, 'deck') - 1)
            setQty(c.id, 'side', qtyOf(c.id, 'side') + 1)
          },
        },
        deltaOf: (c) => qtyOf(c.id, 'deck') - (base[draftKey(c.id, 'deck')] ?? 0),
      }
    : undefined
  const sideControls: CardControls | undefined = viewingCurrent
    ? {
        change: (c, d) => setQty(c.id, 'side', qtyOf(c.id, 'side') + d),
        move: {
          label: '↩ Deck',
          title: 'Return a copy to the deck',
          run: (c) => {
            setQty(c.id, 'side', qtyOf(c.id, 'side') - 1)
            setQty(c.id, 'deck', qtyOf(c.id, 'deck') + 1)
          },
        },
        deltaOf: (c) => qtyOf(c.id, 'side') - (base[draftKey(c.id, 'side')] ?? 0),
      }
    : undefined
  // También con cambios sin guardar: lo que está en la caja guarda su orden al momento y lo añadido, en el borrador.
  const canReorderNow = viewingCurrent && onReorder
  const listCards = (): DeckListCard[] =>
    Object.entries(listing).map(([k, n]) => {
      const [id, part] = k.split(':')
      return { bandai_id: Number(id), section: part === 'side' ? 'side' : 'main', quantity: n }
    })

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
    if (!leader) issues.push({ level: 'error', text: 'The Leader card is missing' })
    if (stats.total < MAIN_MIN) {
      const n = MAIN_MIN - stats.total
      issues.push({ level: 'error', text: `${n} ${n === 1 ? 'card' : 'cards'} short of ${MAIN_MIN}` })
    } else if (stats.total > MAIN_MAX) {
      const n = stats.total - MAIN_MAX
      issues.push({ level: 'error', text: `${n} ${n === 1 ? 'card' : 'cards'} too many (max ${MAIN_MAX})` })
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
        issues.push({ level: 'error', text: `${num} ${e.name}: ${e.n} copies (max ${MAX_COPIES})` })
        e.ids.forEach((id) => flagged.set(id, `More than ${MAX_COPIES} copies`))
      }
    }
    for (const c of [...main, ...zDeck]) {
      if (c.legality === 'banned') {
        issues.push({ level: 'error', text: `${c.card_number} ${c.name} is Banned` })
        flagged.set(c.id, 'Banned')
      } else if (c.legality === 'limited' && (byNumber.get(c.card_number)?.n ?? 0) > 1) {
        issues.push({ level: 'error', text: `${c.card_number} ${c.name} is Limited: 1 copy max` })
        flagged.set(c.id, 'Limited')
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
          issues.push({ level: 'error', text: `${rule.label} (you have ${n})` })
          withSkill.forEach((c) => flagged.set(c.id, rule.label))
        }
      }
    }
    if (leaders.length > 1) issues.push({ level: 'warn', text: `There are ${leaders.length} Leader cards in the deck` })
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
    const full = [...order, ...side.map((c) => c.id).filter((id) => !order.includes(id))]
    // Las de la caja que el borrador ha quitado siguen en la ubicación: conservan su sitio por si vuelven.
    cards.forEach((c, i) => {
      if (!full.includes(c.id)) full.splice(Math.min(i, full.length), 0, c.id)
    })
    if (dirty) setDraftState((st) => ({ ...st, order: full }))
    onReorder(full)
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
              title={leader.back_image_url ? 'Click to flip the card' : leader.name}
            >
              <img src={leaderImage} alt={`Leader: ${leader.name}`} referrerPolicy="no-referrer" />
              {leader.back_image_url && <span className="deck-flip">{showFront ? 'Front' : 'Awaken'} ⟲</span>}
            </button>
          ) : (
            <div className="deck-leader-card empty">No Leader</div>
          )}
          {leader && (
            <span className="deck-leader-links">
              <button className="link small" onClick={() => onOpen(leader.id)}>
                {leader.card_number} · details
              </button>
              {viewingCurrent && (
                <button
                  className="link small danger"
                  onClick={() => setQty(leader.id, 'deck', 0)}
                  title="Remove the Leader from the list (add another with “Add card”)"
                >
                  Remove
                </button>
              )}
            </span>
          )}
        </div>

        <div className="deck-summary">
          <p className="deck-eyebrow">Deck{version ? ` · ${versionLabel(version)}` : ''}</p>
          <h2 className="deck-title">{deck.name}</h2>
          {leader && <p className="deck-leader-name">{showFront || !leader.back_name ? leader.name : leader.back_name}</p>}
          <div className="deck-counts">
            <span className={`deck-count ${stats.total >= MAIN_MIN && stats.total <= MAIN_MAX ? 'ok' : 'bad'}`}>
              <strong>{stats.total}</strong>/{MAIN_MAX} Main Deck
            </span>
            <span className="deck-count">
              <strong>{zTotal}</strong> Z Deck
            </span>
            <span className="deck-count">
              <strong>{stats.avg.toFixed(1)}</strong> Av. Energy
            </span>
            {sideTotal > 0 && (
              <span className="deck-count">
                <strong>{sideTotal}</strong> side
              </span>
            )}
          </div>
          {issues.length === 0 ? (
            <span className="deck-check ok">✓ Meets the deck-building rules</span>
          ) : issues.length === 1 ? (
            <span className={`deck-check ${issues[0].level}`}>⚠ {issues[0].text}</span>
          ) : (
            <details className={`deck-check ${issues.some((i) => i.level === 'error') ? 'error' : 'warn'}`}>
              <summary>⚠ {issues.length} deck-building warnings</summary>
              <ul>
                {issues.map((i) => (
                  <li key={i.text}>{i.text}</li>
                ))}
              </ul>
            </details>
          )}
          <DeckExport deck={{ leader, main, z: zDeck, side }} />
          {detail?.pick_list && (
            <button
              type="button"
              className="deck-picks"
              onClick={() => setShowPicks(true)}
              title="Where to get the cards that moved into this deck when you imported it"
            >
              📋 Cards to fetch · <strong>{detail.pick_list.done}/{detail.pick_list.total}</strong> picked
            </button>
          )}
          {showPicks && (
            <PickListDialog
              deckId={deck.id}
              onClose={() => {
                setShowPicks(false)
                reload()
              }}
            />
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
          <figure className="deck-curve" aria-label="Main Deck Energy curve">
            <figcaption>Energy curve</figcaption>
            <div className="deck-bars">
              {stats.bars.map((b) => (
                <button
                  key={b.cost}
                  className={`deck-bar ${onClass(filter.cost.includes(b.cost))}`}
                  title={`Energy ${b.cost}${b.cost === 10 ? '+' : ''}: ${b.n} cards · click to filter`}
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
            <p className="deck-mix-title">Types</p>
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
            <p className="deck-mix-title">Colors</p>
            <div className="deck-colorbar" aria-label="Split by Colors">
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
                ✕ Clear filters
              </button>
            )}
          </div>
        </div>
      </section>

      {detail ? (
        <VersionBar
          detail={detail}
          selected={selected}
          version={version}
          onSelect={setSelected}
          onChanged={reload}
          draftChanges={draftChanges}
          catalog={known}
          onSaveList={() => setSaving(true)}
          onDiscard={discard}
          onRestored={(result) => {
            setSelected(null)
            setRestored(result)
            reload()
            onCollectionChanged?.()
          }}
        />
      ) : historyError ? (
        <p className="muted small">Couldn't load the deck versions: {historyError}</p>
      ) : null}
      {restored && (
        <p className={`deck-check ${restored.missing.length ? 'warn' : 'ok'} restore-done`}>
          {restored.missing.length ? '⚠' : '✓'} Main list updated: {restored.moved_out} copies out of the deck and{' '}
          {restored.moved_in} in.
          {restored.missing.length > 0 &&
            ` Missing ${restored.missing
              .map((m) => `${m.quantity}× ${catalog[m.bandai_id]?.card_number ?? m.bandai_id}`)
              .join(', ')}.`}{' '}
          <button className="link small" onClick={() => setRestored(null)}>
            Close
          </button>
        </p>
      )}

      <DeckSection
        title="Main Deck"
        count={stats.total}
        shown={filtering ? countOf(shown(main)) : undefined}
        cards={shown(main)}
        flagged={flagged}
        onOpen={onOpen}
        controls={deckControls}
        onAdd={viewingCurrent && !filtering ? () => setPicking(true) : undefined}
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
          controls={deckControls}
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
          controls={sideControls}
          empty={
            filtering
              ? 'No side cards match these filters.'
              : viewingCurrent
                ? 'No cards in the side. Use “→ Side” on a deck card to set copies aside.'
                : undefined
          }
        />
      )}
      {canReorderNow && !filtering && <p className="reorder-hint">Drag the cards to reorder them within their section (on mobile, press and hold a card).</p>}

      {picking && <CardPicker onPick={addCard} quantityOf={(id) => qtyOf(id, 'deck')} onClose={() => setPicking(false)} />}
      {saving && detail && (
        <SaveListModal
          deckId={deck.id}
          nextNumber={(detail.versions[0]?.number ?? 0) + 1}
          cards={listCards()}
          onClose={() => setSaving(false)}
          onSaved={(result) => {
            setSaving(false)
            const order = draftOrder
            discard()
            setSelected(null)
            if (result) {
              setRestored(result)
              // Lo añadido ya está en la caja: se coloca donde lo dejaste al arrastrar.
              const placed = order.length ? api.reorderCollection(deck.id, order).catch(() => {}) : Promise.resolve()
              void placed.then(() => onCollectionChanged?.())
            }
            reload()
          }}
        />
      )}
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
  controls,
  onAdd,
  shown,
  empty = shown != null ? 'No cards match these filters.' : 'No cards.',
}: {
  title: string
  count: number
  /** Con filtros: copias que se ven. */
  shown?: number
  cards: CardSummary[]
  flagged: Map<number, string>
  onOpen: (id: number) => void
  onReorder?: (ids: number[]) => void
  controls?: CardControls
  /** Hueco con forma de carta para añadir una carta nueva a la lista. */
  onAdd?: () => void
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
          <SortableDeckCard key={c.id} card={c} flag={flagged.get(c.id)} onOpen={onOpen} controls={controls} />
        ) : (
          <li key={c.id}>
            <DeckCard card={c} flag={flagged.get(c.id)} onOpen={onOpen} controls={controls} />
          </li>
        ),
      )}
      {onAdd && (
        <li>
          <button className="deck-add" onClick={onAdd} title="Add a card to the list">
            <span aria-hidden>+</span>
            Add card
          </button>
        </li>
      )}
    </ul>
  )
  return (
    <section className="deck-section">
      <h3>
        {title} <span>{shown != null ? `${shown} of ${count}` : count} cards</span>
      </h3>
      {cards.length === 0 && !onAdd ? (
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
  controls,
}: {
  card: CardSummary
  flag?: string
  onOpen: (id: number) => void
  controls?: CardControls
}) {
  const { listeners, setNodeRef, transform, transition, isDragging } = useSortable({ id: card.id })
  return (
    <li
      ref={setNodeRef}
      className={`sortable ${isDragging ? 'dragging' : ''}`}
      style={{ transform: CSS.Transform.toString(transform), transition }}
      {...listeners}
    >
      <DeckCard card={card} flag={flag} onOpen={onOpen} controls={controls} />
    </li>
  )
}

/** Llevar el mazo que se está viendo (la lista principal o la versión elegida) a Time Chamber o copiarlo en texto. */
function DeckExport({ deck }: { deck: ExportDeck }) {
  const [copy, setCopy] = useState<'idle' | 'copied' | 'manual'>('idle')
  if (!isExportable(deck)) return null
  const text = deckListText(deck)
  const copyList = async () => {
    try {
      await navigator.clipboard.writeText(text)
      setCopy('copied')
      window.setTimeout(() => setCopy('idle'), 2000)
    } catch {
      setCopy('manual')
    }
  }
  return (
    <div className="deck-export">
      <a
        className="btn small"
        href={timeChamberUrl(deck)}
        target="_blank"
        rel="noreferrer"
        title="Open this list in the Time Chamber deck builder and simulator (Leader, Main, Z and Side Deck)"
      >
        Open in Time Chamber ↗
      </a>
      <button type="button" className="btn small ghost" onClick={copyList} title="Copy the list as text, e.g. to paste it in TCGArena or Discord">
        {copy === 'copied' ? 'Deck list copied ✓' : 'Copy deck list'}
      </button>
      {copy === 'manual' && (
        <textarea className="input deck-export-text" readOnly value={text} rows={8} onFocus={(e) => e.currentTarget.select()} autoFocus />
      )}
    </div>
  )
}

function DeckCard({
  card,
  flag,
  onOpen,
  controls,
}: {
  card: CardSummary
  flag?: string
  onOpen: (id: number) => void
  controls?: CardControls
}) {
  const n = copies(card)
  const delta = controls?.deltaOf(card) ?? 0
  const stop = (e: React.PointerEvent) => e.stopPropagation()
  // Banned y Limited llevan su color (rojo / ámbar); el resto de avisos, rojo.
  const kind = flag === 'Banned' ? 'banned' : flag === 'Limited' ? 'limited' : undefined
  return (
    <div className={`deck-card-wrap ${delta > 0 ? 'added' : delta < 0 ? 'removed' : ''}`}>
      <button
        className={`deck-card ${flag ? 'flagged' : ''} ${kind ? `flag-${kind}` : ''}`}
        onClick={() => onOpen(card.id)}
        title={`${card.card_number} · ${card.name}`}
      >
        <img src={cardThumb(card)} alt={card.name} loading="lazy" referrerPolicy="no-referrer" draggable={false} />
        <span className="deck-qty" aria-label={`${n} copies`}>
          {n}
        </span>
        {delta !== 0 && (
          <span className="deck-delta" title="Unsaved change compared with what's in the box">
            {delta > 0 ? `+${delta}` : `−${-delta}`}
          </span>
        )}
        {flag && <span className={`deck-flag ${kind ?? ''}`}>{flag}</span>}
        <span className="deck-card-name">
          <small>{card.card_number}</small>
          {card.name}
        </span>
      </button>
      {controls && (
        <div className="deck-card-controls" onPointerDown={stop}>
          <button onClick={() => controls.change(card, -1)} title="Remove a copy" aria-label={`Remove a copy of ${card.name}`}>
            −
          </button>
          <button className="deck-card-move" onClick={() => controls.move.run(card)} title={controls.move.title}>
            {controls.move.label}
          </button>
          <button onClick={() => controls.change(card, 1)} title="Add a copy" aria-label={`Add a copy of ${card.name}`}>
            +
          </button>
        </div>
      )}
    </div>
  )
}
