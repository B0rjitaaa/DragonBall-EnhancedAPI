import { useEffect, useState, type ReactNode } from 'react'
import { api } from '../lib/api'
import { PRICE_LOW_HINT, formatEur, priceLabel } from '../lib/prices'
import { CATEGORY_LABEL, type SkillIndex } from '../lib/skills'
import type { CardDetail, CardPrice, SkillCategory } from '../lib/types'
import CardText from './CardText'
import Tooltip from './Tooltip'

interface Props {
  id: number
  skills: SkillIndex
  onClose: () => void
  onFilter: (field: string, value: string) => void
  /** Mi colección: copias de la carta por ubicación (se pinta bajo el título). */
  children?: ReactNode
}

const HIDDEN_CONFIG = new Set(['Notes'])

export default function CardModal({ id, skills, onClose, onFilter, children }: Props) {
  const [card, setCard] = useState<CardDetail | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [side, setSide] = useState<'front' | 'back'>('front')

  // El componente se monta con key={id}, así que el estado arranca limpio para cada carta
  useEffect(() => {
    api.card(id).then(setCard).catch((e: Error) => setError(e.message))
  }, [id])

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => e.key === 'Escape' && onClose()
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [onClose])

  const back = side === 'back' && card?.has_back
  const config = card ? (back ? card.back_config : card.config) : {}
  const cardSkills: [SkillCategory, string[]][] = card
    ? [
        ['timing', card.timing],
        ['skill', card.keyword_skills],
        ['keyword', card.keyword_rules],
      ]
    : []
  const deckRules = card ? card.keyword_skills.map((s) => skills.deckRule(s)).filter(Boolean) : []

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal" role="dialog" aria-modal="true" onClick={(e) => e.stopPropagation()}>
        <button className="icon-btn close" onClick={onClose} aria-label="Cerrar">
          ✕
        </button>
        {error && <p className="error">{error}</p>}
        {!card && !error && <p className="muted">Cargando…</p>}
        {card && (
          <div className="detail">
            <div className="detail-img">
              <img src={back ? card.back_image_url : card.image_url} alt={card.name} referrerPolicy="no-referrer" />
              {card.has_back && (
                <div className="seg">
                  <button className={side === 'front' ? 'on' : ''} onClick={() => setSide('front')}>
                    Cara frontal
                  </button>
                  <button className={side === 'back' ? 'on' : ''} onClick={() => setSide('back')}>
                    Cara trasera
                  </button>
                </div>
              )}
            </div>
            <div className="detail-info">
              <p className="muted small">
                {card.card_number} · {card.card_set}
              </p>
              <h2>{back ? card.back_name : card.name}</h2>
              {card.price && <PriceBox price={card.price} />}
              {card.legality !== 'legal' && (
                <div className={`legal-banner ${card.legality}`}>
                  <strong>{card.legality === 'banned' ? '⛔ Banned en torneos oficiales' : '⚠️ Limited: máximo 1 copia'}</strong>
                  {card.legality === 'banned'
                    ? ' — no puede incluirse en el mazo ni en el side deck.'
                    : ' entre mazo y side deck.'}
                  {card.legality_since && <small> {card.legality_since}</small>}
                </div>
              )}
              {deckRules.length > 0 && (
                <div className="legal-banner deck">
                  <strong>🃏 Construcción de mazo:</strong> {deckRules.join(' · ')}
                </div>
              )}
              {card.errata && (
                <div className="legal-banner errata">
                  <strong>✎ Errata oficial{card.errata.date && <small> {card.errata.date}</small>}</strong>
                  <div className="errata-cols">
                    <div>
                      <span className="errata-tag">Antes</span>
                      <p>{card.errata.before}</p>
                    </div>
                    <div>
                      <span className="errata-tag after">Después</span>
                      <p>{card.errata.after}</p>
                    </div>
                  </div>
                  {card.errata.notes && <p className="errata-notes">{card.errata.notes}</p>}
                </div>
              )}
              {children}
              <CardText text={back ? card.back_text : card.text} skills={skills} onKeyword={(kw) => onFilter('keyword', kw)} />

              <table className="attrs">
                <tbody>
                  {Object.entries(config)
                    .filter(([k, v]) => v && !HIDDEN_CONFIG.has(k))
                    .map(([k, v]) => (
                      <tr key={k}>
                        <th>{k}</th>
                        <td>{v}</td>
                      </tr>
                    ))}
                </tbody>
              </table>

              {cardSkills.some(([, names]) => names.length > 0) && (
                <>
                  <h3>Keyword skills de esta carta</h3>
                  <dl className="glossary">
                    {cardSkills.flatMap(([category, names]) =>
                      names.map((name) => {
                        const skill = skills.describe(name)
                        return (
                          <div key={`${category}-${name}`} className="glossary-item">
                            <dt>
                              <Tooltip text={`Filtrar por [${name}]`}>
                                <button className="chip" onClick={() => onFilter(skills.fieldFor(name), name)}>
                                  {name}
                                </button>
                              </Tooltip>
                              <small>{CATEGORY_LABEL[category]}</small>
                            </dt>
                            <dd>{skill?.description ?? 'No aparece en la página oficial de keyword skills.'}</dd>
                          </div>
                        )
                      }),
                    )}
                  </dl>
                </>
              )}
              {card.special_traits.length > 0 && (
                <>
                  <h3>Rasgos</h3>
                  <div className="chips">
                    {card.special_traits.map((t) => (
                      <button key={t} className="chip" onClick={() => onFilter('special_trait', t)}>
                        {t}
                      </button>
                    ))}
                  </div>
                </>
              )}
              {card.rulings.length > 0 && (
                <details className="rulings">
                  <summary>
                    Preguntas y respuestas <span className="count">{card.rulings.length}</span>
                  </summary>
                  <dl className="qa">
                    {card.rulings.map((r) => (
                      <div key={r.order} className="qa-item">
                        <dt>
                          <span className="qa-q">P{r.order}</span>
                          {r.is_new && <span className="qa-new">nueva</span>}
                          {r.question}
                        </dt>
                        <dd>{r.answer}</dd>
                      </div>
                    ))}
                  </dl>
                </details>
              )}
              {card.notes && <p className="muted small">Notas: {card.notes.split('|').pop()}</p>}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

/** Precio de mercado en Europa (Cardmarket), de dónde sale y las ofertas en España y en Europa. */
function PriceBox({ price }: { price: CardPrice }) {
  const details = [
    price.low != null && `desde ${formatEur(price.low)} en Europa`,
    price.trend != null && `Trend ${formatEur(price.trend)}`,
    price.avg30 != null && `media 30 días ${formatEur(price.avg30)}`,
  ].filter(Boolean)
  return (
    <div className={`price-box ${price.is_low || price.suspect ? 'is-low' : ''}`}>
      <span className="price-main">{priceLabel(price)}</span>
      <span className="price-what small">
        {price.manual
          ? 'precio puesto a mano'
          : price.suspect
            ? 'precio dudoso: un solo anuncio, sin ventas (no cuenta en el valor)'
            : price.is_low ? 'anuncio más barato en Europa (sin ventas)' : 'precio de mercado en Europa'}
      </span>
      {!price.manual && (
        <span className="price-details muted small">{price.is_low ? PRICE_LOW_HINT : details.join(' · ')}</span>
      )}
      <span className="price-links small">
        <a href={price.url_es} target="_blank" rel="noreferrer">Ofertas en España ↗</a>
        <a href={price.url} target="_blank" rel="noreferrer">Ofertas en Europa ↗</a>
      </span>
    </div>
  )
}
