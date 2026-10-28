import { useEffect, useState, type ReactNode } from 'react'
import { api } from '../lib/api'
import { cardLink, showCardRef } from '../lib/cardLink'
import { formatEur, priceLabel } from '../lib/prices'
import PriceChart from './PriceChart'
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
  /** Abrir otra impresión del mismo número (fila «Otras impresiones»). */
  onOpenPrint?: (id: number) => void
}

const HIDDEN_CONFIG = new Set(['Notes'])

export default function CardModal({ id, skills, onClose, onFilter, children, onOpenPrint }: Props) {
  const [card, setCard] = useState<CardDetail | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [side, setSide] = useState<'front' | 'back'>('front')

  // El componente se monta con key={id}, así que el estado arranca limpio para cada carta
  useEffect(() => {
    api.card(id).then(setCard).catch((e: Error) => setError(e.message))
  }, [id])

  // Abierta la carta, la dirección lleva su número (?card=BT20-149), también si se abrió por id.
  useEffect(() => {
    if (card && new URLSearchParams(window.location.search).has('card')) showCardRef(card.ref)
  }, [card])

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
              {card.prints.length > 1 && (
                <section className="card-prints">
                  <strong className="small">Impresiones de {card.card_number}</strong>
                  <div>
                    {card.prints.map((p) => (
                      <button
                        key={p.id}
                        className={p.id === card.id ? 'on' : ''}
                        onClick={() => p.id !== card.id && onOpenPrint?.(p.id)}
                        disabled={!onOpenPrint && p.id !== card.id}
                        title={`${p.ref} · ${p.rarity_code} · ${p.card_set}`}
                      >
                        <img src={p.thumb_url} alt="" loading="lazy" referrerPolicy="no-referrer" />
                        <span>{p.rarity_code || '—'}</span>
                      </button>
                    ))}
                  </div>
                </section>
              )}
              {card.price && card.price.counts && <PriceChart points={card.price_history ?? []} />}
            </div>
            <div className="detail-info">
              <p className="muted small detail-meta">
                <span>
                  {card.card_number} · {card.card_set}
                </span>
                <CopyLink cardRef={card.ref} />
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

const SOURCE_LABEL = { cardmarket: 'Cardmarket', tcgplayer: 'TCGplayer', manual: 'a mano' } as const

/** Variación en tanto por uno → «▲ 12 %» / «▼ 5 %». */
function Change({ label, value }: { label: string; value: number | null | undefined }) {
  if (value == null) return null
  const pct = Math.round(value * 100)
  if (pct === 0) return <span className="price-change flat">{label}: =</span>
  return (
    <span className={`price-change ${pct > 0 ? 'up' : 'down'}`}>
      {label}: {pct > 0 ? '▲' : '▼'} {Math.abs(pct)} %
    </span>
  )
}

/** El precio de la carta: de dónde sale (Cardmarket, TCGplayer o a mano), su variación y los enlaces a
 * las ofertas en España y Europa (Cardmarket) y en TCGplayer. Su evolución va bajo la foto (PriceChart). */
function PriceBox({ price }: { price: CardPrice }) {
  const what = price.manual
    ? 'precio puesto a mano'
    : price.suspect && !price.counts
      ? 'precio dudoso: un solo anuncio, sin ventas (no cuenta en el valor)'
      : !price.counts
        ? 'solo lo que pide un vendedor: sin ventas (no cuenta en el valor)'
        : `precio de mercado · ${SOURCE_LABEL[price.source]}`
  const sources = [
    price.cardmarket_eur != null && `Cardmarket ${formatEur(price.cardmarket_eur)}`,
    price.tcgplayer_eur != null && `TCGplayer ${formatEur(price.tcgplayer_eur)} (EE. UU.)`,
    price.low != null && `desde ${formatEur(price.low)} en Europa`,
  ].filter(Boolean)
  return (
    <div className={`price-box ${price.counts ? '' : 'is-low'}`}>
      <span className="price-main">{priceLabel(price)}</span>
      <span className="price-what small">{what}</span>
      {!price.manual && sources.length > 0 && <span className="price-details muted small">{sources.join(' · ')}</span>}
      {(price.change_7 != null || price.change_30 != null) && (
        <span className="price-changes small">
          <Change label="7 días" value={price.change_7} />
          <Change label="30 días" value={price.change_30} />
        </span>
      )}
      <span className="price-links small">
        <a href={price.url_es} target="_blank" rel="noreferrer">Ofertas en España ↗</a>
        <a href={price.url} target="_blank" rel="noreferrer">Ofertas en Europa ↗</a>
        {price.tcg_url && <a href={price.tcg_url} target="_blank" rel="noreferrer">TCGplayer ↗</a>}
      </span>
    </div>
  )
}

/** Copia el enlace a esta carta (la página actual con ?card=BT20-149): al abrirlo, sale este detalle. */
function CopyLink({ cardRef }: { cardRef: string }) {
  const [state, setState] = useState<'idle' | 'copied' | 'manual'>('idle')
  const link = cardLink(cardRef)
  const copy = async () => {
    try {
      await navigator.clipboard.writeText(link)
      setState('copied')
      window.setTimeout(() => setState('idle'), 2000)
    } catch {
      setState('manual')
    }
  }
  if (state === 'manual') {
    return <input className="input copy-link-input" readOnly value={link} onFocus={(e) => e.currentTarget.select()} autoFocus />
  }
  return (
    <button type="button" className="link small copy-link" onClick={copy} title={link}>
      {state === 'copied' ? 'Enlace copiado ✓' : '🔗 Copiar enlace'}
    </button>
  )
}
