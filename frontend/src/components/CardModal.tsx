import { useEffect, useState } from 'react'
import { api } from '../lib/api'
import { CATEGORY_LABEL, type SkillIndex } from '../lib/skills'
import type { CardDetail, SkillCategory } from '../lib/types'
import CardText from './CardText'
import Tooltip from './Tooltip'

interface Props {
  id: number
  skills: SkillIndex
  onClose: () => void
  onFilter: (field: string, value: string) => void
}

const HIDDEN_CONFIG = new Set(['Notes'])

export default function CardModal({ id, skills, onClose, onFilter }: Props) {
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
              {card.legality !== 'legal' && (
                <div className={`legal-banner ${card.legality}`}>
                  <strong>{card.legality === 'banned' ? '⛔ Prohibida en torneos oficiales' : '⚠️ Limitada: máximo 1 copia'}</strong>
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
              {card.notes && <p className="muted small">Notas: {card.notes.split('|').pop()}</p>}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
