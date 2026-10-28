import {
  DndContext, KeyboardSensor, MouseSensor, TouchSensor, closestCenter, useSensor, useSensors, type DragEndEvent,
} from '@dnd-kit/core'
import { SortableContext, arrayMove, rectSortingStrategy, sortableKeyboardCoordinates, useSortable } from '@dnd-kit/sortable'
import { CSS } from '@dnd-kit/utilities'
import { useCallback, useEffect, useRef, useState, type ReactNode } from 'react'
import { KIND_LABELS } from './components/OwnedPanel'
import { api } from './lib/api'
import { colorClass } from './lib/colors'
import { formatEur } from './lib/prices'
import { locationPath } from './lib/query'
import type { HistoryCard, Location, LocationKind } from './lib/types'

const KINDS = Object.entries(KIND_LABELS) as [LocationKind, string][]
const SECTIONS: { kind: LocationKind; title: string; add: string; placeholder: string }[] = [
  { kind: 'deck', title: 'Mazos', add: 'Nuevo mazo', placeholder: 'Nombre del mazo (p. ej. Goku azul)' },
  { kind: 'binder', title: 'Archivadores', add: 'Nuevo archivador', placeholder: 'Nombre del archivador' },
  { kind: 'storage', title: 'Almacén', add: 'Nueva caja', placeholder: 'Nombre (p. ej. Caja 7)' },
  { kind: 'other', title: 'Otras', add: 'Nueva ubicación', placeholder: 'Nombre de la ubicación' },
]

/** Enlace a Mi colección dentro de una ubicación. */
export const collectionUrl = (loc: Location): string => locationPath(loc)

type Run = (action: () => Promise<unknown>) => Promise<void>

// Momento en que terminó el último arrastre: el clic que lanza el navegador al soltar no debe abrir el enlace.
let lastDragEnd = 0
function swallowClickAfterDrag(e: MouseEvent) {
  if (Date.now() - lastDragEnd < 400) {
    e.preventDefault()
    e.stopPropagation()
  }
}

const formatDate = (iso: string | null) =>
  iso ? new Date(iso).toLocaleDateString('es-ES', { day: 'numeric', month: 'short', year: 'numeric' }) : ''

/** Cuántas veces ha pasado un mazo al histórico. */
const timesParked = (deck: Location) => deck.status_log?.filter((e) => e.status === 'parked').length ?? 0

/** Pantalla de ubicaciones de Mi colección: mazos (en uso y en el histórico), archivadores y almacén. */
export default function LocationsPage() {
  useEffect(() => {
    document.addEventListener('click', swallowClickAfterDrag, true)
    return () => document.removeEventListener('click', swallowClickAfterDrag, true)
  }, [])
  const [locations, setLocations] = useState<Location[] | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  const [editing, setEditing] = useState<Location | null>(null)
  const [logOf, setLogOf] = useState<Location | null>(null)
  const [retiring, setRetiring] = useState<Location | null>(null)
  const [toast, setToast] = useState<{ text: string; href?: string } | null>(null)
  const [current, setCurrent] = useState<LocationKind>('deck')

  const reload = useCallback(() => {
    api
      .locations()
      .then((l) => {
        setLocations(l)
        setError(null)
      })
      .catch((e: Error) => setError(e.message))
  }, [])
  useEffect(reload, [reload])

  useEffect(() => {
    if (!toast) return
    const t = window.setTimeout(() => setToast(null), 10000)
    return () => window.clearTimeout(t)
  }, [toast])

  // Pestaña activa según la sección que se está viendo.
  useEffect(() => {
    if (!locations) return
    const observer = new IntersectionObserver(
      (entries) => {
        const visible = entries.filter((e) => e.isIntersecting).sort((a, b) => a.boundingClientRect.top - b.boundingClientRect.top)
        if (visible[0]) setCurrent(visible[0].target.id.replace('sec-', '') as LocationKind)
      },
      { rootMargin: '-110px 0px -55% 0px' },
    )
    document.querySelectorAll('.loc-section[id]').forEach((el) => observer.observe(el))
    return () => observer.disconnect()
  }, [locations])

  const run: Run = async (action) => {
    setBusy(true)
    try {
      await action()
      setError(null)
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e))
    } finally {
      setBusy(false)
      reload()
    }
  }

  if (!locations) {
    return <div className="locations-page">{error ? <p className="error">{error}</p> : <p className="muted">Cargando…</p>}</div>
  }

  const unplaced = locations.find((l) => l.is_default)
  const custom = locations.filter((l) => !l.is_default)
  const ofKind = (k: LocationKind) => custom.filter((l) => l.kind === k)

  // Reordenar dentro de un grupo: se reescriben las posiciones de todas, en el orden de las secciones.
  const saveOrder = (ids: number[]) => {
    const moved = new Set(ids)
    const byId = new Map(custom.map((l) => [l.id, l]))
    const order: Location[] = []
    for (const l of custom.slice().sort((a, b) => SECTIONS.findIndex((s) => s.kind === a.kind) - SECTIONS.findIndex((s) => s.kind === b.kind))) {
      if (!moved.has(l.id)) order.push(l)
      else if (l.id === custom.find((c) => moved.has(c.id))!.id) order.push(...ids.map((id) => byId.get(id)!))
    }
    setLocations([...(unplaced ? [unplaced] : []), ...order.map((l, pos) => ({ ...l, position: pos + 1 }))])
    void run(() =>
      Promise.all(order.map((l, pos) => (l.position === pos + 1 ? null : api.updateLocation(l.id, { position: pos + 1 })))),
    )
  }

  // Al histórico se pasa desde su diálogo (las copias salen del mazo); al volver a usarlo solo entra su líder.
  const setStatus = (loc: Location, status: Location['status']) => {
    if (status === 'parked') {
      setRetiring(loc)
      return
    }
    void run(async () => {
      const { leader } = await api.deckBackInUse(loc.id)
      const brought = leader
        ? `Su Leader (${leader.card_number}${leader.fake ? ', falsa' : ''}) ha pasado de «${leader.from}» al mazo.`
        : 'No tienes ninguna copia de su Leader para traerla.'
      setToast({ text: `«${loc.name}» vuelve a estar en uso. ${brought} El resto lo recuperas restaurando su última versión.`, href: collectionUrl(loc) })
    })
  }

  const decks = ofKind('deck')
  const counts = Object.fromEntries(SECTIONS.map((s) => [s.kind, ofKind(s.kind).length])) as Record<LocationKind, number>

  return (
    <div className="locations-page">
      <header className="locations-page-head">
        <h1>Ubicaciones</h1>
        <p className="muted">
          Dónde guardas tus copias. Para mover cartas de un sitio a otro, usa la{' '}
          <a href="/collection?view=list">lista de Mi colección</a>.
        </p>
      </header>

      <nav className="loc-tabs" aria-label="Secciones">
        {SECTIONS.filter((s) => s.kind !== 'other' || counts.other > 0).map((s) => (
          <a key={s.kind} href={`#sec-${s.kind}`} className={current === s.kind ? 'active' : ''}>
            {s.title} <span>{counts[s.kind]}</span>
          </a>
        ))}
      </nav>

      {error && <p className="error">{error}</p>}
      {unplaced && unplaced.copies > 0 && (
        <a className="loc-unplaced" href={collectionUrl(unplaced)}>
          <strong>{unplaced.copies}</strong> {unplaced.copies === 1 ? 'copia sin ubicar' : 'copias sin ubicar'}
          <span>Ordenarlas →</span>
        </a>
      )}

      <DeckSection decks={decks} busy={busy} run={run} onEdit={setEditing} onStatus={setStatus} onLog={setLogOf} onOrder={saveOrder} />
      {SECTIONS.filter((s) => s.kind !== 'deck' && (s.kind !== 'other' || counts.other > 0)).map((s) => (
        <ListSection key={s.kind} section={s} items={ofKind(s.kind)} busy={busy} run={run} onEdit={setEditing} onOrder={saveOrder} />
      ))}

      {editing && <EditDialog loc={editing} run={run} onClose={() => setEditing(null)} />}
      {logOf && <LogDialog deck={logOf} onClose={() => setLogOf(null)} />}
      {retiring && (
        <HistoryDialog
          deck={retiring}
          unplaced={unplaced}
          onDone={reload}
          onClose={() => setRetiring(null)}
        />
      )}
      {toast && (
        <div className="loc-toast" role="status">
          {toast.text}
          {toast.href && (
            <a className="btn ghost" href={toast.href}>
              Abrir el mazo
            </a>
          )}
        </div>
      )}
    </div>
  )
}

/** Cabecera de sección con «Ordenar» y «+ Nuevo…», y el formulario de alta cuando se abre. */
function SectionHead({
  section, count, sorting, onSort, run, busy, nextPosition,
}: {
  section: (typeof SECTIONS)[number]
  count: number
  sorting: boolean
  onSort?: () => void
  run: Run
  busy: boolean
  nextPosition: number
}) {
  const [adding, setAdding] = useState(false)
  const [name, setName] = useState('')
  return (
    <>
      <div className="loc-section-head">
        <h2>
          {section.title} <small>{count}</small>
        </h2>
        <div className="loc-section-tools">
          {onSort && count > 1 && (
            <button className={`btn ghost ${sorting ? 'on' : ''}`} onClick={onSort}>
              {sorting ? 'Listo' : 'Ordenar'}
            </button>
          )}
          <button className="btn" onClick={() => setAdding((v) => !v)} aria-expanded={adding}>
            + {section.add}
          </button>
        </div>
      </div>
      {adding && (
        <form
          className="loc-add"
          onSubmit={(e) => {
            e.preventDefault()
            const value = name.trim()
            if (!value) return
            void run(async () => {
              await api.createLocation(value, section.kind, nextPosition)
              setName('')
              setAdding(false)
            })
          }}
        >
          <input
            className="input"
            autoFocus
            placeholder={section.placeholder}
            value={name}
            maxLength={80}
            onChange={(e) => setName(e.target.value)}
            onKeyDown={(e) => e.key === 'Escape' && setAdding(false)}
            aria-label={section.add}
          />
          <button className="btn primary" disabled={busy || !name.trim()}>
            Crear
          </button>
          <button type="button" className="btn ghost" onClick={() => setAdding(false)}>
            Cancelar
          </button>
        </form>
      )}
    </>
  )
}

/** Lista reordenable por arrastre (solo en modo «Ordenar»). */
function SortableList({
  ids, onOrder, className, children,
}: {
  ids: number[]
  onOrder: (ids: number[]) => void
  className: string
  children: ReactNode
}) {
  const sensors = useSensors(
    useSensor(MouseSensor, { activationConstraint: { distance: 6 } }),
    useSensor(TouchSensor, { activationConstraint: { delay: 200, tolerance: 6 } }),
    useSensor(KeyboardSensor, { coordinateGetter: sortableKeyboardCoordinates }),
  )
  const onDragEnd = ({ active, over }: DragEndEvent) => {
    lastDragEnd = Date.now()
    if (over && active.id !== over.id) onOrder(arrayMove(ids, ids.indexOf(Number(active.id)), ids.indexOf(Number(over.id))))
  }
  return (
    <DndContext sensors={sensors} collisionDetection={closestCenter} onDragEnd={onDragEnd} onDragCancel={() => (lastDragEnd = Date.now())}>
      <SortableContext items={ids} strategy={rectSortingStrategy}>
        <div className={`${className} sorting`}>{children}</div>
      </SortableContext>
    </DndContext>
  )
}

function Sortable({ id, children }: { id: number; children: (dragging: boolean) => ReactNode }) {
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } = useSortable({ id })
  return (
    <div ref={setNodeRef} className="loc-sortable" style={{ transform: CSS.Transform.toString(transform), transition }} {...attributes} {...listeners}>
      {children(isDragging)}
    </div>
  )
}

function DeckSection({
  decks, busy, run, onEdit, onStatus, onLog, onOrder,
}: {
  decks: Location[]
  busy: boolean
  run: Run
  onEdit: (l: Location) => void
  onStatus: (l: Location, s: Location['status']) => void
  onLog: (l: Location) => void
  onOrder: (ids: number[]) => void
}) {
  const [sorting, setSorting] = useState(false)
  const active = decks.filter((d) => d.status !== 'parked')
  const parked = decks
    .filter((d) => d.status === 'parked')
    .sort((a, b) => (b.parked_at ?? '').localeCompare(a.parked_at ?? ''))
  const section = SECTIONS[0]
  const tile = (d: Location, handle = false, dragging = false) => (
    <DeckTile key={d.id} deck={d} busy={busy} sorting={sorting} handle={handle} dragging={dragging}
      menu={<LocMenu loc={d} onEdit={onEdit} onStatus={onStatus} onLog={onLog} />} />
  )
  return (
    <section className="loc-section" id="sec-deck">
      <SectionHead section={section} count={decks.length} sorting={sorting} onSort={() => setSorting((v) => !v)}
        run={run} busy={busy} nextPosition={(decks.at(-1)?.position ?? 0) + 1} />
      <h3 className="loc-sub">
        En uso <small>{active.length}</small>
      </h3>
      {active.length ? (
        sorting ? (
          <SortableList ids={active.map((d) => d.id)} onOrder={onOrder} className="locdeck-grid">
            {active.map((d) => (
              <Sortable key={d.id} id={d.id}>
                {(dragging) => tile(d, true, dragging)}
              </Sortable>
            ))}
          </SortableList>
        ) : (
          <div className="locdeck-grid">{active.map((d) => tile(d))}</div>
        )
      ) : (
        <p className="empty small">No tienes ningún mazo en uso.</p>
      )}

      {parked.length > 0 && (
        <details className="locdeck-parked">
          <summary>
            Histórico <small>{parked.length}</small>
            <span className="muted"> · mazos que ya no usas; su última lista queda guardada</span>
          </summary>
          <ul>
            {parked.map((d) => (
              <li key={d.id}>
                <a className="locdeck-parked-main" href={collectionUrl(d)}>
                  {d.leader ? <img src={d.leader.image} alt="" loading="lazy" referrerPolicy="no-referrer" /> : <span className="locdeck-thumb-empty" />}
                  <span>
                    <strong>{d.name}</strong>
                    <small className="muted">
                      {d.copies > 0 ? `${d.copies} copias en la caja` : `${d.last_list ?? 0} cartas en su última lista`}
                      {' · '}en el histórico desde el {formatDate(d.parked_at)}
                      {timesParked(d) > 1 && ` · ${timesParked(d)}.ª vez`}
                    </small>
                  </span>
                </a>
                <button className="btn" disabled={busy} onClick={() => onStatus(d, 'active')}>
                  Volver a usar
                </button>
                <LocMenu loc={d} onEdit={onEdit} onStatus={onStatus} onLog={onLog} />
              </li>
            ))}
          </ul>
        </details>
      )}
    </section>
  )
}

function DeckTile({
  deck, menu, sorting, handle, dragging,
}: {
  deck: Location
  busy: boolean
  menu: ReactNode
  sorting: boolean
  handle?: boolean
  dragging: boolean
}) {
  const issues = deck.issues
  const warnings = [
    issues?.banned.length && `${issues.banned.length} Banned`,
    issues?.limited.length && `${issues.limited.length} Limited repetida${issues.limited.length > 1 ? 's' : ''}`,
  ].filter(Boolean)
  return (
    <article className={`locdeck-tile ${dragging ? 'dragging' : ''}`}>
      <a className="locdeck-art" href={sorting ? undefined : collectionUrl(deck)} draggable={false}>
        {deck.leader ? (
          <img src={deck.leader.image} alt={`Leader: ${deck.leader.name}`} loading="lazy" referrerPolicy="no-referrer" draggable={false} />
        ) : (
          <span className="locdeck-art-empty">Sin Leader</span>
        )}
        {deck.leader && (
          <span className="locdeck-colors">
            {deck.leader.colors.map((c) => (
              <i key={c} className={`dot ${colorClass(c)}`} title={c} />
            ))}
          </span>
        )}
      </a>
      <div className="locdeck-body">
        <div className="locdeck-title">
          <a href={sorting ? undefined : collectionUrl(deck)}>
            <strong>{deck.name}</strong>
          </a>
          {sorting && handle ? (
            <span className="drag-handle" aria-hidden="true">⠿</span>
          ) : (
            menu
          )}
        </div>
        {deck.leader && <small className="muted locdeck-leader-name">{deck.leader.name}</small>}
        <p className="locdeck-stats">
          <strong>{deck.copies}</strong> copias · {deck.cards} cartas
          {!!deck.value && <> · <span title="Valor en Cardmarket (sin las falsas)">{formatEur(deck.value)}</span></>}
          {deck.fakes > 0 && <> · <a className="fake-link" href={`${collectionUrl(deck)}?fakes=1`}>{deck.fakes === 1 ? '1 falsa' : `${deck.fakes} falsas`}</a></>}
        </p>
        {warnings.length > 0 && (
          <p className="locdeck-warn" title={[...(issues?.banned ?? []), ...(issues?.limited ?? [])].join(', ')}>
            ⚠ {warnings.join(' · ')}
          </p>
        )}
      </div>
    </article>
  )
}

function ListSection({
  section, items, busy, run, onEdit, onOrder,
}: {
  section: (typeof SECTIONS)[number]
  items: Location[]
  busy: boolean
  run: Run
  onEdit: (l: Location) => void
  onOrder: (ids: number[]) => void
}) {
  const [sorting, setSorting] = useState(false)
  const max = Math.max(1, ...items.map((l) => l.copies))
  const row = (l: Location, handle = false, dragging = false) => (
    <div key={l.id} className={`loc-row ${dragging ? 'dragging' : ''}`}>
      <a className="loc-row-main" href={sorting ? undefined : collectionUrl(l)}>
        <span className="loc-row-name">
          <strong>{l.name}</strong>
          {l.notes && <small className="muted">{l.notes}</small>}
        </span>
        <span className="loc-row-stats">
          <strong>{l.copies}</strong> copias · {l.cards} cartas
          {!!l.value && <> · <span title="Valor en Cardmarket (sin las falsas)">{formatEur(l.value)}</span></>}
          {l.fakes > 0 && <em className="fake-text"> · {l.fakes === 1 ? '1 falsa' : `${l.fakes} falsas`}</em>}
        </span>
        <span className="loc-bar" aria-hidden="true">
          <i style={{ width: `${(100 * l.copies) / max}%` }} />
        </span>
      </a>
      {sorting && handle ? (
        <span className="drag-handle" aria-hidden="true">⠿</span>
      ) : (
        <LocMenu loc={l} onEdit={onEdit} />
      )}
    </div>
  )
  return (
    <section className="loc-section" id={`sec-${section.kind}`}>
      <SectionHead section={section} count={items.length} sorting={sorting} onSort={() => setSorting((v) => !v)}
        run={run} busy={busy} nextPosition={(items.at(-1)?.position ?? 0) + 1} />
      {!items.length ? (
        <p className="empty small">Aún no hay ninguna.</p>
      ) : sorting ? (
        <SortableList ids={items.map((l) => l.id)} onOrder={onOrder} className="loc-rows">
          {items.map((l) => (
            <Sortable key={l.id} id={l.id}>
              {(dragging) => row(l, true, dragging)}
            </Sortable>
          ))}
        </SortableList>
      ) : (
        <div className="loc-rows">{items.map((l) => row(l))}</div>
      )}
    </section>
  )
}

/** Menú «⋯» de una ubicación: editar y, en los mazos, moverlo al histórico o volver a usarlo. */
function LocMenu({
  loc, onEdit, onStatus, onLog,
}: {
  loc: Location
  onEdit: (l: Location) => void
  onStatus?: (l: Location, s: Location['status']) => void
  onLog?: (l: Location) => void
}) {
  const [open, setOpen] = useState(false)
  const ref = useRef<HTMLDivElement>(null)
  useEffect(() => {
    if (!open) return
    const close = (e: MouseEvent) => !ref.current?.contains(e.target as Node) && setOpen(false)
    const esc = (e: KeyboardEvent) => e.key === 'Escape' && setOpen(false)
    document.addEventListener('mousedown', close)
    document.addEventListener('keydown', esc)
    return () => {
      document.removeEventListener('mousedown', close)
      document.removeEventListener('keydown', esc)
    }
  }, [open])
  const pick = (fn: () => void) => () => {
    setOpen(false)
    fn()
  }
  return (
    <div className="loc-menu" ref={ref}>
      <button className="icon-btn" aria-label={`Opciones de ${loc.name}`} aria-expanded={open} onClick={() => setOpen((v) => !v)}>
        ⋯
      </button>
      {open && (
        <div className="loc-menu-list" role="menu">
          <button role="menuitem" onClick={pick(() => onEdit(loc))}>
            Editar…
          </button>
          {onStatus &&
            (loc.status === 'parked' ? (
              <button role="menuitem" onClick={pick(() => onStatus(loc, 'active'))}>
                Volver a usar
              </button>
            ) : (
              <button role="menuitem" onClick={pick(() => onStatus(loc, 'parked'))}>
                Mover al histórico
              </button>
            ))}
          {onLog && !!loc.status_log?.length && (
            <button role="menuitem" onClick={pick(() => onLog(loc))}>
              Registro de uso…
            </button>
          )}
        </div>
      )}
    </div>
  )
}

/** Editar nombre, tipo y notas; y borrar, con confirmación dentro del propio diálogo. */
function EditDialog({ loc, run, onClose }: { loc: Location; run: Run; onClose: () => void }) {
  const ref = useRef<HTMLDialogElement>(null)
  const [name, setName] = useState(loc.name)
  const [kind, setKind] = useState<LocationKind>(loc.kind)
  const [notes, setNotes] = useState(loc.notes)
  const [confirmDelete, setConfirmDelete] = useState(false)
  useEffect(() => {
    ref.current?.showModal()
  }, [])
  const save = () => {
    const changes: Partial<Pick<Location, 'name' | 'kind' | 'notes'>> = {}
    if (name.trim() && name.trim() !== loc.name) changes.name = name.trim()
    if (kind !== loc.kind) changes.kind = kind
    if (notes !== loc.notes) changes.notes = notes
    if (Object.keys(changes).length) void run(() => api.updateLocation(loc.id, changes))
    onClose()
  }
  return (
    <dialog ref={ref} className="loc-dialog" onClose={onClose} onClick={(e) => e.target === ref.current && onClose()}>
      <form
        method="dialog"
        onSubmit={(e) => {
          e.preventDefault()
          save()
        }}
      >
        <h2>Editar ubicación</h2>
        <label>
          Nombre
          <input className="input" value={name} maxLength={80} onChange={(e) => setName(e.target.value)} autoFocus />
        </label>
        <label>
          Tipo
          <select className="input" value={kind} onChange={(e) => setKind(e.target.value as LocationKind)}>
            {KINDS.map(([v, l]) => (
              <option key={v} value={v}>
                {l}
              </option>
            ))}
          </select>
        </label>
        <label>
          Notas
          <textarea className="input" rows={3} maxLength={500} value={notes} placeholder="p. ej. caja azul del armario"
            onChange={(e) => setNotes(e.target.value)} />
        </label>
        {confirmDelete ? (
          <div className="loc-dialog-danger">
            <p>
              {loc.copies
                ? `¿Borrar «${loc.name}»? Sus ${loc.copies} copias pasarán a «Sin ubicar».`
                : `¿Borrar «${loc.name}»?`}
            </p>
            <div className="loc-dialog-actions">
              <button type="button" className="btn ghost" onClick={() => setConfirmDelete(false)}>
                No, mantener
              </button>
              <button
                type="button"
                className="btn danger"
                onClick={() => {
                  void run(() => api.deleteLocation(loc.id))
                  onClose()
                }}
              >
                Sí, borrar
              </button>
            </div>
          </div>
        ) : (
          <div className="loc-dialog-actions">
            <button type="button" className="btn ghost danger-text" onClick={() => setConfirmDelete(true)}>
              Borrar…
            </button>
            <span className="spacer" />
            <button type="button" className="btn ghost" onClick={onClose}>
              Cancelar
            </button>
            <button className="btn primary">Guardar</button>
          </div>
        )}
      </form>
    </dialog>
  )
}

/** Pasar un mazo al histórico: confirma con la lista de copias que salen y, al hacerlo, la deja a mano
 * (copiable) porque esas copias quedan en «Sin ubicar» hasta que las guardes en otro sitio. */
function HistoryDialog({
  deck, unplaced, onDone, onClose,
}: {
  deck: Location
  unplaced?: Location
  onDone: () => void
  onClose: () => void
}) {
  const ref = useRef<HTMLDialogElement>(null)
  const [cards, setCards] = useState<HistoryCard[] | null>(null)
  const [done, setDone] = useState(false)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [copied, setCopied] = useState(false)
  useEffect(() => {
    ref.current?.showModal()
    api
      .deckHistoryPreview(deck.id)
      .then((r) => setCards(r.cards))
      .catch((e: Error) => setError(e.message))
  }, [deck.id])

  const copies = (cards ?? []).reduce((n, c) => n + c.quantity, 0)
  const distinct = new Set((cards ?? []).map((c) => c.bandai_id)).size
  const asText = () =>
    (cards ?? []).map((c) => `${c.quantity}x ${c.card_number} ${c.name}${c.fake ? ' (falsa)' : ''}`).join('\n')

  const confirm = async () => {
    setSaving(true)
    try {
      const r = await api.moveDeckToHistory(deck.id)
      setCards(r.cards)
      setDone(true)
      onDone()
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e))
    } finally {
      setSaving(false)
    }
  }
  const copy = async () => {
    try {
      await navigator.clipboard.writeText(asText())
      setCopied(true)
    } catch {
      setError('No se pudo copiar: selecciona la lista y cópiala a mano')
    }
  }

  return (
    <dialog ref={ref} className="loc-dialog history-dialog" onClose={onClose}>
      <div className="history-body">
        {done ? (
          <>
            <h2>«{deck.name}» está en el histórico</h2>
            <p>
              Estas <strong>{copies} copias</strong> ({distinct} cartas) están ahora en <strong>«Sin ubicar»</strong>. Guárdalas
              donde quieras cuando puedas. Su lista queda guardada en el mazo.
            </p>
          </>
        ) : (
          <>
            <h2>Mover «{deck.name}» al histórico</h2>
            <p className="muted">
              {cards === null
                ? 'Cargando sus cartas…'
                : cards.length
                  ? `Sus ${copies} copias (${distinct} cartas) pasarán a «Sin ubicar». La lista del mazo queda guardada como versión, para que puedas montarlo otra vez.`
                  : 'El mazo está vacío: solo pasará al histórico.'}
            </p>
          </>
        )}
        {error && <p className="error">{error}</p>}
        {cards && cards.length > 0 && (
          <ul className="history-list">
            {cards.map((c) => (
              <li key={`${c.bandai_id}-${c.fake}`}>
                <span className="history-qty">{c.quantity}×</span>
                <img src={c.image} alt="" loading="lazy" referrerPolicy="no-referrer" />
                <span className="history-num">{c.card_number}</span>
                <span className="history-name">
                  {c.name}
                  {c.card_type === 'LEADER' && <em> · Leader</em>}
                  {c.fake && <em className="fake-text"> · falsa</em>}
                </span>
              </li>
            ))}
          </ul>
        )}
        <div className="loc-dialog-actions">
          {done ? (
            <>
              <button type="button" className="btn ghost" onClick={copy}>
                {copied ? 'Copiada ✓' : 'Copiar lista'}
              </button>
              <span className="spacer" />
              {unplaced && (
                <a className="btn" href={collectionUrl(unplaced)}>
                  Ver «Sin ubicar»
                </a>
              )}
              <button type="button" className="btn primary" onClick={() => ref.current?.close()}>
                Cerrar
              </button>
            </>
          ) : (
            <>
              <span className="spacer" />
              <button type="button" className="btn ghost" onClick={() => ref.current?.close()} disabled={saving}>
                Cancelar
              </button>
              <button type="button" className="btn primary" onClick={confirm} disabled={saving || cards === null}>
                {saving ? 'Moviendo…' : 'Mover al histórico'}
              </button>
            </>
          )}
        </div>
      </div>
    </dialog>
  )
}

/** Registro de uso de un mazo: cuándo pasó al histórico (y cuántas copias salieron) y cuándo volvió a usarse. */
function LogDialog({ deck, onClose }: { deck: Location; onClose: () => void }) {
  const ref = useRef<HTMLDialogElement>(null)
  useEffect(() => ref.current?.showModal(), [])
  const log = deck.status_log ?? []
  const times = timesParked(deck)
  return (
    <dialog ref={ref} className="loc-dialog log-dialog" onClose={onClose}>
      <div className="history-body">
        <h2>Registro de uso de «{deck.name}»</h2>
        <p className="muted">
          Ha pasado {times === 1 ? 'una vez' : `${times} veces`} al histórico. Ahora está{' '}
          <strong>{deck.status === 'parked' ? 'en el histórico' : 'en uso'}</strong>.
        </p>
        <ol className="log-list">
          {log.map((e, i) => (
            <li key={i} className={e.status}>
              <time dateTime={e.at}>
                {formatDate(e.at)}
                <small>{new Date(e.at).toLocaleTimeString('es-ES', { hour: '2-digit', minute: '2-digit' })}</small>
              </time>
              <span>
                {e.status === 'parked' ? (
                  <>
                    <strong>Al histórico</strong>
                    <small className="muted">
                      {e.copies ? `${e.copies} copias pasaron a «Sin ubicar»` : 'con la caja vacía'}
                    </small>
                  </>
                ) : (
                  <strong>Vuelve a usarse</strong>
                )}
              </span>
            </li>
          ))}
        </ol>
        <div className="loc-dialog-actions">
          <span className="spacer" />
          <button type="button" className="btn primary" onClick={() => ref.current?.close()}>
            Cerrar
          </button>
        </div>
      </div>
    </dialog>
  )
}
