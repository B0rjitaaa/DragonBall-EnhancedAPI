import { useEffect, useState } from 'react'
import { api } from '../lib/api'
import type { CardDetail } from '../lib/types'
import CardText from './CardText'

interface Props {
  id: number
  onClose: () => void
  onFilter: (field: string, value: string) => void
}

const HIDDEN_CONFIG = new Set(['Notes'])

export default function CardModal({ id, onClose, onFilter }: Props) {
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
              <CardText text={back ? card.back_text : card.text} onKeyword={(kw) => onFilter('keyword', kw)} />

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

              {card.keywords.length > 0 && (
                <>
                  <h3>Habilidades</h3>
                  <div className="chips">
                    {card.keywords.map((kw) => (
                      <button key={kw} className="chip" onClick={() => onFilter('keyword', kw)}>
                        {kw}
                      </button>
                    ))}
                  </div>
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
