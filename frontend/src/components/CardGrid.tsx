import { colorClass } from '../lib/colors'
import type { SkillIndex } from '../lib/skills'
import type { CardSummary } from '../lib/types'

// Etiqueta corta en el listado para las keyword skills que limitan la construcción del mazo
const DECK_BADGES: Record<string, string> = { Ultimate: '1 COPIA', 'Super Combo': 'SC ≤4', 'Dragon Ball': 'DB ≤7' }

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
  emptyText?: string
}

export default function CardGrid({ cards, loading, skills, onOpen, quantities, emptyText, onAdjust, adjusting }: Props) {
  if (!loading && cards.length === 0) {
    return <div className="empty">{emptyText ?? 'No hay cartas que cumplan estos filtros.'}</div>
  }
  return (
    <ul className={`grid ${loading ? 'loading' : ''}`}>
      {cards.map((c) => (
        <li key={c.id}>
          <button className={`tile ${c.legality === 'banned' ? 'is-banned' : ''}`} onClick={() => onOpen(c.id)} title={`${c.card_number} · ${c.name}`}>
            <div className="tile-img">
              <img
                src={c.image_url}
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
              {c.has_back && <span className="badge">2 caras</span>}
              {(c.fakes ?? 0) > 0 && (
                <span className="fake-badge tile-fake" title="Copias falsas en tu colección">
                  {c.fakes === 1 ? '1 falsa' : `${c.fakes} falsas`}
                </span>
              )}
              {quantities?.[c.id] != null && !onAdjust && (
                <span className="qty-badge" title={`${quantities[c.id]} copias en tu colección`}>
                  ×{quantities[c.id]}
                </span>
              )}
              {c.legality !== 'legal' && (
                <span className={`legal-badge ${c.legality}`} title={c.legality_since}>
                  {c.legality === 'banned' ? 'BAN' : 'LIMIT 1'}
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
                  {c.power != null && <>✊{c.power.toLocaleString('es-ES')}</>}
                </span>
              </div>
              {c.locations && c.locations.length > 0 && (
                <div
                  className="tile-loc"
                  title={c.locations.map((l) => `${l.name}${l.fake ? ' (falsas)' : ''}: ${l.quantity}`).join('\n')}
                >
                  {c.locations.length === 1
                    ? `${c.locations[0].name}${c.locations[0].fake ? ' (falsa)' : ''}`
                    : c.locations.map((l) => `${l.name}${l.fake ? ' (falsa)' : ''} ×${l.quantity}`).join(' · ')}
                </div>
              )}
            </div>
          </button>
          {onAdjust && quantities?.[c.id] != null && (
            // Fuera del botón de la carta: pulsar − / + no abre la ficha.
            <div className="qty-controls" aria-label={`Copias de ${c.name}`}>
              <button
                className="qty-btn"
                onClick={() => onAdjust(c.id, -1)}
                disabled={adjusting?.has(c.id)}
                aria-label="Quitar una copia"
                title="Quitar una copia"
              >
                −
              </button>
              <span className="qty-value" title="Copias en tu colección">×{quantities[c.id]}</span>
              <button
                className="qty-btn"
                onClick={() => onAdjust(c.id, 1)}
                disabled={adjusting?.has(c.id)}
                aria-label="Añadir una copia"
                title="Añadir una copia"
              >
                +
              </button>
            </div>
          )}
        </li>
      ))}
    </ul>
  )
}
