import { DndContext, MouseSensor, TouchSensor, closestCenter, useSensor, useSensors, type DragEndEvent } from '@dnd-kit/core'
import { SortableContext, arrayMove, rectSortingStrategy, useSortable } from '@dnd-kit/sortable'
import { CSS } from '@dnd-kit/utilities'
import type { ReactNode } from 'react'
import { colorClass } from '../lib/colors'
import type { SkillIndex } from '../lib/skills'
import type { CardSummary } from '../lib/types'
import { cardThumb } from '../lib/types'

// Etiqueta corta en el listado para las keyword skills que limitan la construcción del mazo
const DECK_BADGES: Record<string, string> = { Ultimate: '1 COPY', 'Super Combo': 'SC ≤4', 'Dragon Ball': 'DB ≤7' }

interface Props {
  cards: CardSummary[]
  loading: boolean
  skills: SkillIndex
  onOpen: (id: number) => void
  /** Mi colección: copias de cada carta. */
  quantities?: Record<number, number>
  /** Mi colección: botones − / + para restar o sumar copias. */
  onAdjust?: (id: number, delta: number) => void
  /** Cartas con un cambio de copias en curso (botones desactivados). */
  adjusting?: Set<number>
  /** Mi colección: con false, las copias falsas no se muestran (ni su ubicación ni el aviso). */
  showFakes?: boolean
  emptyText?: string
  /** Mi colección dentro de una ubicación, en «Mi orden»: arrastrar para reordenar (ids en el nuevo orden). */
  onReorder?: (ids: number[]) => void
}

/** Una tarjeta arrastrable (el arrastre empieza tras mover unos píxeles o mantener pulsado en el móvil). */
function SortableTile({ id, children }: { id: number; children: ReactNode }) {
  // Sin los atributos de accesibilidad de dnd-kit (role="button", tabIndex): la tarjeta ya
  // tiene sus propios botones y el teclado sigue usándolos con normalidad.
  const { listeners, setNodeRef, transform, transition, isDragging } = useSortable({ id })
  return (
    <li
      ref={setNodeRef}
      className={`sortable ${isDragging ? 'dragging' : ''}`}
      style={{ transform: CSS.Transform.toString(transform), transition }}
      {...listeners}
    >
      {children}
    </li>
  )
}

export default function CardGrid({
  cards, loading, skills, onOpen, quantities, emptyText, onAdjust, adjusting, showFakes = true, onReorder,
}: Props) {
  // Ratón: tras 6 px (un clic sigue abriendo la ficha). Táctil: mantener pulsado 250 ms (el desplazamiento sigue funcionando).
  const sensors = useSensors(
    useSensor(MouseSensor, { activationConstraint: { distance: 6 } }),
    useSensor(TouchSensor, { activationConstraint: { delay: 250, tolerance: 6 } }),
  )
  if (!loading && cards.length === 0) {
    return <div className="empty">{emptyText ?? 'No cards match these filters.'}</div>
  }
  const tile = (c: CardSummary) => {
    const locs = (c.locations ?? []).filter((l) => showFakes || !l.fake)
    return (
      <>
          <button className={`tile ${c.legality === 'banned' ? 'is-banned' : ''}`} onClick={() => onOpen(c.id)} title={`${c.card_number} · ${c.name}`}>
            <div className="tile-img">
              <img
                src={cardThumb(c)}
                alt=""
                loading="lazy"
                referrerPolicy="no-referrer"
                onError={(e) => e.currentTarget.classList.add('broken')}
              />
              <span className="img-fallback">{c.card_number}</span>
              {c.keyword_skills
                .filter((k) => DECK_BADGES[k])
                .map((k) => (
                  <span key={k} className="deck-badge" title={skills.deckRule(k)}>
                    {DECK_BADGES[k]}
                  </span>
                ))}
              {c.has_back && <span className="badge">2 sides</span>}
              {showFakes && (c.fakes ?? 0) > 0 && (
                <span className="fake-badge tile-fake" title="Fake copies in your collection">
                  {c.fakes === 1 ? '1 fake' : `${c.fakes} fakes`}
                </span>
              )}
              {quantities?.[c.id] != null && !onAdjust && (
                <span className="qty-badge" title={`${quantities[c.id]} copies in your collection`}>
                  ×{quantities[c.id]}
                </span>
              )}
              {c.legality !== 'legal' && (
                <span className={`legal-badge ${c.legality}`} title={c.legality_since}>
                  {c.legality === 'banned' ? 'BAN' : 'LIMIT 1'}
                </span>
              )}
              {(c.has_errata || c.rulings_count > 0) && (
                <span className="card-marks">
                  {c.has_errata && (
                    <span className="mark errata" title="Has an official erratum">✎</span>
                  )}
                  {c.rulings_count > 0 && (
                    <span className="mark qa" title={`${c.rulings_count} official Q&As`}>
                      ?{c.rulings_count}
                    </span>
                  )}
                </span>
              )}
            </div>
            <div className="tile-body">
              <div className="tile-title">{c.name}</div>
              <div className="tile-meta">
                <span>{c.card_number}</span>
                <span className="dots">
                  {c.colors.map((col) => (
                    <i key={col} className={`dot ${colorClass(col)}`} title={col} />
                  ))}
                </span>
              </div>
              <div className="tile-meta muted">
                <span>{c.card_type}</span>
                <span>
                  {c.energy != null && <>⚡{c.energy} </>}
                  {c.power != null && <>✊{c.power.toLocaleString('en-GB')}</>}
                </span>
              </div>
              {locs.length > 0 && (
                <div
                  className="tile-loc"
                  title={locs.map((l) => `${l.name}${l.fake ? ' (fakes)' : ''}: ${l.quantity}`).join('\n')}
                >
                  {locs.length === 1
                    ? `${locs[0].name}${locs[0].fake ? ' (fake)' : ''}`
                    : locs.map((l) => `${l.name}${l.fake ? ' (fake)' : ''} ×${l.quantity}`).join(' · ')}
                </div>
              )}
            </div>
          </button>
          {onAdjust && quantities?.[c.id] != null && (
            // Fuera del botón de la carta: pulsar − / + no abre la ficha.
            <div className="qty-controls" aria-label={`Copies of ${c.name}`}>
              <button
                className="qty-btn"
                onClick={() => onAdjust(c.id, -1)}
                disabled={adjusting?.has(c.id)}
                aria-label="Remove a copy"
                title="Remove a copy"
              >
                −
              </button>
              <span className="qty-value" title="Copies in your collection">×{quantities[c.id]}</span>
              <button
                className="qty-btn"
                onClick={() => onAdjust(c.id, 1)}
                disabled={adjusting?.has(c.id)}
                aria-label="Add a copy"
                title="Add a copy"
              >
                +
              </button>
            </div>
          )}
      </>
    )
  }

  if (onReorder) {
    const ids = cards.map((c) => c.id)
    const onDragEnd = ({ active, over }: DragEndEvent) => {
      if (!over || active.id === over.id) return
      onReorder(arrayMove(ids, ids.indexOf(Number(active.id)), ids.indexOf(Number(over.id))))
    }
    return (
      <DndContext sensors={sensors} collisionDetection={closestCenter} onDragEnd={onDragEnd}>
        <SortableContext items={ids} strategy={rectSortingStrategy}>
          <ul className={`grid sortable-grid ${loading ? 'loading' : ''}`}>
            {cards.map((c) => (
              <SortableTile key={c.id} id={c.id}>
                {tile(c)}
              </SortableTile>
            ))}
          </ul>
        </SortableContext>
      </DndContext>
    )
  }

  return (
    <ul className={`grid ${loading ? 'loading' : ''}`}>
      {cards.map((c) => (
        <li key={c.id}>{tile(c)}</li>
      ))}
    </ul>
  )
}
