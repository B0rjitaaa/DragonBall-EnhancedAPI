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
}

export default function CardGrid({ cards, loading, skills, onOpen }: Props) {
  if (!loading && cards.length === 0) {
    return <div className="empty">No hay cartas que cumplan estos filtros.</div>
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
            </div>
          </button>
        </li>
      ))}
    </ul>
  )
}
