// Vista de archivador de un Binder (/locations/binder/<uid>): sus páginas como un archivador abierto, con cada
// copia en su bolsillo. Se pueden mover copias arrastrando (o tocando una carta y luego el bolsillo), dejarlas
// «sin colocar» y meter, quitar o reordenar páginas. Las posiciones son las notas de las copias («P. 12 · row
// 2 · col 3», ver backend/collection/binder.py).
import { DndContext, MouseSensor, TouchSensor, useDraggable, useDroppable, useSensor, useSensors, type DragEndEvent } from '@dnd-kit/core'
import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { api } from './lib/api'
import { collectionUrl } from './LocationsPage'
import type { BinderData, BinderSpot, CardSummary, Location } from './lib/types'
import { cardThumb } from './lib/types'

type Selected = BinderSpot | null
const spotKey = (s: BinderSpot) => ('page' in s ? `p:${s.page}:${s.slot}` : `u:${s.bandai_id}:${s.fake ? 1 : 0}`)
const parseKey = (key: string): BinderSpot | null => {
  const [kind, a, b] = key.split(':')
  if (kind === 'p') return { page: Number(a), slot: Number(b) }
  if (kind === 'u') return { bandai_id: Number(a), fake: b === '1' }
  return null
}

function uidFromPath(): string {
  return window.location.pathname.replace(/\/+$/, '').split('/').pop() ?? ''
}

export default function BinderPage() {
  const [loc, setLoc] = useState<Location | null>(null)
  const [data, setData] = useState<BinderData | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  const [first, setFirst] = useState(1) // primera página a la vista
  const [selected, setSelected] = useState<Selected>(null)
  const [query, setQuery] = useState('')
  const [narrow, setNarrow] = useState(() => window.innerWidth < 900)
  const perView = narrow ? 1 : 2

  useEffect(() => {
    const onResize = () => setNarrow(window.innerWidth < 900)
    window.addEventListener('resize', onResize)
    return () => window.removeEventListener('resize', onResize)
  }, [])

  useEffect(() => {
    const uid = uidFromPath()
    api
      .locations()
      .then((all) => {
        const found = all.find((l) => l.uid === uid && l.kind === 'binder')
        if (!found) throw new Error("This binder doesn't exist (or isn't a binder any more)")
        setLoc(found)
        document.title = `${found.name} · Binder`
        return api.binder(found.id)
      })
      .then(setData)
      .catch((e: Error) => setError(e.message))
  }, [])

  const run = useCallback(async (action: () => Promise<BinderData>) => {
    setBusy(true)
    setError(null)
    try {
      setData(await action())
    } catch (e) {
      setError((e as Error).message)
    } finally {
      setBusy(false)
      setSelected(null)
    }
  }, [])

  const pages = data?.pages ?? 1
  // En dos páginas, como un libro: la 1 sale sola a la derecha (a la izquierda, el interior de la tapa) y
  // luego 2-3, 4-5…; si la última es par, sale sola a la izquierda. 0 o más allá de la última = hueco.
  const left = perView === 2 ? first - (first % 2) : first
  const spread = perView === 2 ? [left, left + 1] : [first]
  const visible = spread.filter((p) => p >= 1 && p <= pages)
  const start = visible[0] ?? 1
  const canBack = perView === 2 ? left > 0 : first > 1
  const canForward = spread[spread.length - 1] < pages
  const go = useCallback((delta: number) => setFirst((f) => Math.min(Math.max(1, f + delta * perView), pages)), [perView, pages])
  const [adding, setAdding] = useState(false)
  // La casilla de página: lo que se escribe no se aplica hasta Intro o al salir (así se puede borrar y escribir).
  const [jump, setJump] = useState<string | null>(null)
  const shownPage = visible.includes(first) ? first : start
  const applyJump = () => {
    if (jump != null && jump.trim() !== '') setFirst(Math.min(Math.max(1, Math.round(Number(jump)) || 1), pages))
    setJump(null)
  }
  // Bolsillo vacío tocado sin carta cogida: se elige qué carta va ahí.
  const [filling, setFilling] = useState<{ page: number; slot: number } | null>(null)

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if ((e.target as HTMLElement).closest('input, textarea, select')) return
      if (e.key === 'ArrowLeft') go(-1)
      if (e.key === 'ArrowRight') go(1)
      if (e.key === 'Escape') setSelected(null)
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [go])

  const bySpot = useMemo(() => {
    const m = new Map<string, { bandai_id: number; fake: boolean; count: number }>()
    for (const s of data?.slots ?? []) m.set(`${s.page}:${s.slot}`, s)
    return m
  }, [data])

  // Con una carta cogida de un bolsillo con varias copias: mover todas (por defecto) o solo una.
  const [justOne, setJustOne] = useState(false)
  const move = (source: BinderSpot, target: { page: number; slot: number } | null, one = false) => {
    if (!data) return
    if (target && 'page' in source && source.page === target.page && source.slot === target.slot) return
    setJustOne(false)
    void run(() => api.binderMove(data.binder.id, source, target, one))
  }
  const pageAction = (action: 'insert-page' | 'delete-page' | 'move-page', page: number, to?: number) => {
    if (!data) return
    void run(() => api.binderPage(data.binder.id, action, page, to))
  }

  const sensors = useSensors(
    useSensor(MouseSensor, { activationConstraint: { distance: 6 } }),
    useSensor(TouchSensor, { activationConstraint: { delay: 250, tolerance: 6 } }),
  )
  const onDragEnd = ({ active, over }: DragEndEvent) => {
    const source = parseKey(String(active.id))
    if (!source || !over) return
    const target = String(over.id)
    if (target === 'tray') {
      if ('page' in source) move(source, null)
    } else {
      const spot = parseKey(target)
      if (spot && 'page' in spot) move(source, spot)
    }
  }
  // Tocar: primero la carta, luego el bolsillo (o la bandeja) de destino. Sirve en el móvil y para páginas lejanas.
  const tapCard = (spot: BinderSpot) => setSelected((s) => (s && spotKey(s) === spotKey(spot) ? null : spot))
  const tapPocket = (page: number, slot: number) => {
    if (selected) move(selected, { page, slot }, justOne)
    else setFilling({ page, slot })
  }

  if (error && !data) return <main className="binder-page"><p className="error">{error}</p></main>
  if (!data || !loc) return <main className="binder-page"><p className="muted">Loading the binder…</p></main>

  const placed = data.placed
  const pickedCount = selected && 'page' in selected ? (bySpot.get(`${selected.page}:${selected.slot}`)?.count ?? 1) : 1
  const unplacedTotal = data.unplaced.reduce((n, u) => n + u.quantity, 0)
  const card = (id: number): CardSummary | undefined => data.catalog[id]
  const q = query.trim().toLowerCase()
  const tray = data.unplaced.filter((u) => {
    const c = card(u.bandai_id)
    return !q || (c && `${c.name} ${c.card_number}`.toLowerCase().includes(q))
  })

  return (
    <main className={`binder-page ${busy ? 'busy' : ''}`}>
      <header className="binder-head">
        <div>
          <a className="muted small" href="/locations">← Locations</a>
          <h1>{data.binder.name}</h1>
          <p className="muted small">
            {data.binder.cols}×{data.binder.rows} · {pages} {pages === 1 ? 'page' : 'pages'} · {data.copies} copies: {placed} placed,{' '}
            {unplacedTotal} not placed · <a href={collectionUrl(loc)}>Open in My collection</a>
          </p>
        </div>
        <div className="binder-nav">
          <button className="btn" onClick={() => setAdding((v) => !v)} aria-expanded={adding}>+ Add page</button>
          <button className="btn" onClick={() => go(-1)} disabled={!canBack} aria-label="Previous pages">‹</button>
          <label className="binder-jump">
            Page
            <input
              className="input"
              type="number"
              min={1}
              max={pages}
              value={jump ?? shownPage}
              onChange={(e) => setJump(e.target.value)}
              onBlur={applyJump}
              onKeyDown={(e) => {
                if (e.key === 'Enter') applyJump()
                if (e.key === 'Escape') setJump(null)
              }}
            />
            of {pages}
          </label>
          <button className="btn" onClick={() => go(1)} disabled={!canForward} aria-label="Next pages">›</button>
        </div>
      </header>
      {adding && (
        <AddPage
          pages={pages}
          around={start}
          onCancel={() => setAdding(false)}
          onAdd={(at) => {
            setAdding(false)
            pageAction('insert-page', at)
            setFirst(at)
          }}
        />
      )}

      {selected && (
        <p className="binder-hint">
          Card picked: tap a pocket to move it there{'page' in selected ? ' (or “Not placed” to take it out)' : ''}. You can change pages first.{' '}
          {pickedCount > 1 && (
            <span className="seg binder-how-many" role="radiogroup" aria-label="How many copies">
              <button type="button" role="radio" aria-checked={!justOne} className={!justOne ? 'on' : ''} onClick={() => setJustOne(false)}>
                All {pickedCount}
              </button>
              <button type="button" role="radio" aria-checked={justOne} className={justOne ? 'on' : ''} onClick={() => setJustOne(true)}>
                Just 1
              </button>
            </span>
          )}{' '}
          <button className="link" onClick={() => setSelected(null)}>Cancel</button>
        </p>
      )}
      {error && <p className="error">{error}</p>}

      <DndContext sensors={sensors} onDragEnd={onDragEnd}>
        <div className="binder-book">
        <button className="binder-turn prev" onClick={() => go(-1)} disabled={!canBack} aria-label="Previous pages" title="Previous pages">‹</button>
        <div className={`binder-spread pages-${spread.length}`}>
          {spread.map((page) => page < 1 || page > pages ? (
            <div key={`blank-${page}`} className="binder-sheet blank" aria-hidden="true">
              <span>{page < 1 ? 'Inside cover' : 'End of the binder'}</span>
            </div>
          ) : (
            <BinderSheet
              key={page}
              page={page}
              pages={pages}
              rows={data.binder.rows}
              cols={data.binder.cols}
              bySpot={bySpot}
              card={card}
              selected={selected}
              onTapCard={tapCard}
              onTapPocket={tapPocket}
              onAction={pageAction}
            />
          ))}
        </div>
        <button className="binder-turn next" onClick={() => go(1)} disabled={!canForward} aria-label="Next pages" title="Next pages">›</button>
        </div>

        <Tray selected={selected} canDropHere={!!selected && 'page' in selected} onTap={() => selected && 'page' in selected && move(selected, null, justOne)}>
          <div className="tray-head">
            <h2>
              Not placed <small>{unplacedTotal}</small>
            </h2>
            <input className="input" type="search" placeholder="Search by name or number…" value={query} onChange={(e) => setQuery(e.target.value)} />
          </div>
          {data.stackable > 0 && (
            <p className="tray-stack">
              <button className="btn small" onClick={() => void run(() => api.binderStack(data.binder.id))}>
                ⧉ Put {data.stackable} loose {data.stackable === 1 ? 'copy' : 'copies'} with their card
              </button>
              <span className="muted small">For cards that already have a pocket: the copies go behind it, in the same pocket.</span>
            </p>
          )}
          {data.unplaced.length === 0 ? (
            <p className="muted small">Every copy has its pocket.</p>
          ) : (
            <ul className="tray-cards">
              {tray.map((u) => (
                <li key={`${u.bandai_id}-${u.fake}`}>
                  <CardChip
                    id={spotKey({ bandai_id: u.bandai_id, fake: u.fake })}
                    card={card(u.bandai_id)}
                    fake={u.fake}
                    count={u.quantity}
                    picked={!!selected && spotKey(selected) === spotKey({ bandai_id: u.bandai_id, fake: u.fake })}
                    onTap={() => tapCard({ bandai_id: u.bandai_id, fake: u.fake })}
                  />
                </li>
              ))}
            </ul>
          )}
        </Tray>
      </DndContext>
      {filling && (
        <PickCard
          spot={filling}
          unplaced={data.unplaced}
          card={card}
          onClose={() => setFilling(null)}
          onPick={(u) => {
            move({ bandai_id: u.bandai_id, fake: u.fake }, filling)
            setFilling(null)
          }}
        />
      )}
      <p className="muted small binder-help">
        Drag a card to another pocket (if it's taken, they swap; if it's the same card, they go together) or to “Not placed”. ×N means N copies in that pocket: dragging moves them all, and with a tap you can move just one. On a phone, or to reach a far page: tap the card, change page and tap the pocket.
      </p>
    </main>
  )
}

function BinderSheet({
  page, pages, rows, cols, bySpot, card, selected, onTapCard, onTapPocket, onAction,
}: {
  page: number
  pages: number
  rows: number
  cols: number
  bySpot: Map<string, { bandai_id: number; fake: boolean; count: number }>
  card: (id: number) => CardSummary | undefined
  selected: Selected
  onTapCard: (spot: BinderSpot) => void
  onTapPocket: (page: number, slot: number) => void
  onAction: (action: 'insert-page' | 'delete-page' | 'move-page', page: number, to?: number) => void
}) {
  const [menu, setMenu] = useState(false)
  const [to, setTo] = useState(page)
  const pockets = Array.from({ length: rows * cols }, (_, i) => i + 1)
  const empty = pockets.every((slot) => !bySpot.has(`${page}:${slot}`))
  return (
    <section className="binder-sheet" aria-label={`Page ${page}`}>
      <div className="sheet-head">
        <strong>Page {page}</strong>
        <span className="sheet-menu">
          <button className="icon-btn" onClick={() => setMenu((v) => !v)} aria-expanded={menu} aria-label={`Options for page ${page}`}>
            ⋯
          </button>
          {menu && (
            <div className="sheet-menu-pop" role="menu">
              <button role="menuitem" onClick={() => (setMenu(false), onAction('insert-page', page))}>Insert an empty page before</button>
              <button role="menuitem" onClick={() => (setMenu(false), onAction('insert-page', page + 1))}>Insert an empty page after</button>
              <form
                className="sheet-move"
                onSubmit={(e) => {
                  e.preventDefault()
                  setMenu(false)
                  onAction('move-page', page, to)
                }}
              >
                Move this page to
                <input className="input" type="number" min={1} max={pages} value={to} onChange={(e) => setTo(Number(e.target.value))} />
                <button className="btn small" disabled={to < 1 || to > pages || to === page}>Move</button>
              </form>
              <button
                role="menuitem"
                className="danger-text"
                disabled={!empty || pages <= 1}
                title={empty ? undefined : 'Only empty pages can be removed'}
                onClick={() => (setMenu(false), onAction('delete-page', page))}
              >
                Remove this page{empty ? '' : ' (it has cards)'}
              </button>
            </div>
          )}
        </span>
      </div>
      {/* Que la página entera quepa en pantalla: el ancho sale del alto disponible (cartas 63×88). */}
      <div
        className="sheet-grid"
        style={{
          gridTemplateColumns: `repeat(${cols}, minmax(0, 1fr))`,
          maxWidth: `calc(${cols} * (min(68vh, 760px) / ${rows}) * 0.716)`,
        }}
      >
        {pockets.map((slot) => {
          const here = bySpot.get(`${page}:${slot}`)
          const spot = { page, slot }
          return (
            <Pocket key={slot} id={spotKey(spot)} onTap={() => !here && onTapPocket(page, slot)} targetable={!!selected}>
              {here ? (
                <CardChip
                  id={spotKey(spot)}
                  card={card(here.bandai_id)}
                  fake={here.fake}
                  count={here.count}
                  picked={!!selected && spotKey(selected) === spotKey(spot)}
                  onTap={() => (selected && spotKey(selected) !== spotKey(spot) ? onTapPocket(page, slot) : onTapCard(spot))}
                />
              ) : (
                <span className="pocket-empty">{slot}</span>
              )}
            </Pocket>
          )
        })}
      </div>
    </section>
  )
}

function Pocket({ id, children, onTap, targetable }: { id: string; children: React.ReactNode; onTap: () => void; targetable: boolean }) {
  const { setNodeRef, isOver } = useDroppable({ id })
  return (
    <div ref={setNodeRef} className={`pocket ${isOver ? 'over' : ''} ${targetable ? 'targetable' : ''}`} onClick={onTap}>
      {children}
    </div>
  )
}

function Tray({ children, onTap, canDropHere }: { children: React.ReactNode; selected: Selected; onTap: () => void; canDropHere: boolean }) {
  const { setNodeRef, isOver } = useDroppable({ id: 'tray' })
  return (
    <section ref={setNodeRef} className={`binder-tray ${isOver ? 'over' : ''} ${canDropHere ? 'targetable' : ''}`} onClick={(e) => e.target === e.currentTarget && onTap()}>
      {canDropHere && (
        <button className="btn small tray-drop" onClick={onTap}>
          ↓ Take the picked card out (Not placed)
        </button>
      )}
      {children}
    </section>
  )
}

function CardChip({
  id, card, fake, count, picked, onTap,
}: {
  id: string
  card?: CardSummary
  fake: boolean
  count?: number
  picked: boolean
  onTap: () => void
}) {
  const { attributes, listeners, setNodeRef, transform, isDragging } = useDraggable({ id })
  const style = transform ? { transform: `translate3d(${transform.x}px, ${transform.y}px, 0)` } : undefined
  return (
    <button
      ref={setNodeRef}
      type="button"
      className={`card-chip ${picked ? 'picked' : ''} ${isDragging ? 'dragging' : ''}`}
      style={style}
      title={card ? `${card.card_number} · ${card.name}${fake ? ' · fake' : ''}` : ''}
      onClick={(e) => {
        e.stopPropagation()
        onTap()
      }}
      {...listeners}
      {...attributes}
    >
      {card ? <img src={cardThumb(card)} alt={card.name} loading="lazy" referrerPolicy="no-referrer" draggable={false} /> : <span>?</span>}
      {fake && <span className="chip-fake">Fake</span>}
      {count != null && count > 1 && <span className="chip-count">×{count}</span>}
      <span className="chip-number">{card?.card_number}</span>
    </button>
  )
}

/** Añadir una página vacía: delante o detrás de la que elijas. */
function AddPage({ pages, around, onAdd, onCancel }: { pages: number; around: number; onAdd: (at: number) => void; onCancel: () => void }) {
  const [page, setPage] = useState(around)
  const [where, setWhere] = useState<'before' | 'after'>('after')
  const ok = page >= 1 && page <= pages
  return (
    <form
      className="binder-add-page"
      onSubmit={(e) => {
        e.preventDefault()
        if (ok) onAdd(where === 'before' ? page : page + 1)
      }}
    >
      <span>Add an empty page</span>
      <span className="seg" role="radiogroup" aria-label="Before or after">
        {(['before', 'after'] as const).map((w) => (
          <button key={w} type="button" role="radio" aria-checked={where === w} className={where === w ? 'on' : ''} onClick={() => setWhere(w)}>
            {w === 'before' ? 'Before' : 'After'}
          </button>
        ))}
      </span>
      <label>
        page
        <input className="input" type="number" min={1} max={pages} value={page} onChange={(e) => setPage(Number(e.target.value))} />
      </label>
      <span className="muted small">
        {ok ? `It will be page ${where === 'before' ? page : page + 1}; the ones after it move up one.` : `Choose a page from 1 to ${pages}.`}
      </span>
      <span className="binder-add-actions">
        <button type="button" className="btn" onClick={onCancel}>Cancel</button>
        <button className="btn primary" disabled={!ok}>Add page</button>
      </span>
    </form>
  )
}

/** Elegir la carta para un bolsillo vacío, entre las copias del archivador que no tienen bolsillo. */
function PickCard({
  spot, unplaced, card, onPick, onClose,
}: {
  spot: { page: number; slot: number }
  unplaced: BinderData['unplaced']
  card: (id: number) => CardSummary | undefined
  onPick: (u: BinderData['unplaced'][number]) => void
  onClose: () => void
}) {
  const ref = useRef<HTMLDialogElement>(null)
  const [query, setQuery] = useState('')
  useEffect(() => {
    ref.current?.showModal()
  }, [])
  const q = query.trim().toLowerCase()
  const list = unplaced.filter((u) => {
    const c = card(u.bandai_id)
    return !q || (c && `${c.name} ${c.card_number}`.toLowerCase().includes(q))
  })
  return (
    <dialog ref={ref} className="loc-dialog pick-card" onClose={onClose}>
      <div className="pick-card-body">
        <header className="pick-card-head">
          <h2>
            Page {spot.page} · pocket {spot.slot}
          </h2>
          <button type="button" className="icon-btn" onClick={() => ref.current?.close()} aria-label="Close">
            ✕
          </button>
        </header>
        <p className="muted small">Choose the card for this pocket, from the copies in this binder that have no pocket yet.</p>
        <input
          className="input"
          type="search"
          placeholder="Search by name or number…"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          autoFocus
        />
        {unplaced.length === 0 ? (
          <p className="muted small">Every copy in this binder already has its pocket. Take one out to “Not placed” first, or drag a card here.</p>
        ) : list.length === 0 ? (
          <p className="muted small">No card matches “{query}”.</p>
        ) : (
          <ul className="pick-card-grid">
            {list.map((u) => {
              const c = card(u.bandai_id)
              return (
                <li key={`${u.bandai_id}-${u.fake}`}>
                  <button type="button" className="pick-card-item" onClick={() => onPick(u)} title={c ? `${c.card_number} · ${c.name}${u.fake ? ' · fake' : ''}` : ''}>
                    {c ? <img src={cardThumb(c)} alt={c.name} loading="lazy" referrerPolicy="no-referrer" /> : <span>?</span>}
                    {u.fake && <span className="chip-fake">Fake</span>}
                    {u.quantity > 1 && <span className="chip-count">×{u.quantity}</span>}
                    <span className="pick-card-name">
                      <small>{c?.card_number}</small>
                      {c?.name}
                    </span>
                  </button>
                </li>
              )
            })}
          </ul>
        )}
      </div>
    </dialog>
  )
}
