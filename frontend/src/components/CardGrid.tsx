import type { CardSummary } from '../lib/types'
import { colorClass } from '../lib/colors'

interface Props {
  cards: CardSummary[]
  loading: boolean
  onOpen: (id: number) => void
}

export default function CardGrid({ cards, loading, onOpen }: Props) {
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
