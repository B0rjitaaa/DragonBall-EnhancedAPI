import { useEffect, useState, type ReactNode } from 'react'
import { api } from '../lib/api'
import { cardLink, showCardRef } from '../lib/cardLink'
import { colorClass } from '../lib/colors'
import { formatEur, priceLabel } from '../lib/prices'
import PriceChart from './PriceChart'
import type { SkillIndex } from '../lib/skills'
import type { CardDetail, CardPrice } from '../lib/types'
import CardText, { errataText } from './CardText'

interface Props {
  id: number
  skills: SkillIndex
  onClose: () => void
  onFilter: (field: string, value: string) => void
  /** Mi colección: copias de la carta por ubicación (se pinta bajo la imagen, en «Your copies»). */
  children?: ReactNode
  /** Abrir otra impresión del mismo número (miniaturas bajo la imagen). */
  onOpenPrint?: (id: number) => void
  /** Carta anterior / siguiente de los resultados (‹ › y las teclas ← →). */
  onPrev?: () => void
  onNext?: () => void
}

const TYPE_LABEL: Record<string, string> = { LEADER: 'Leader', BATTLE: 'Battle', EXTRA: 'Extra', UNISON: 'Unison' }
const typeLabel = (t: string) => TYPE_LABEL[t] ?? t.split('-').map((w) => (w.length <= 1 ? w : w[0] + w.slice(1).toLowerCase())).join('-')

/** «2 red + 1 blue» a partir de ['Red', 'Red', 'Blue']. */
function colorCostText(colors: string[]): string {
  const count = new Map<string, number>()
  for (const c of colors) count.set(c, (count.get(c) ?? 0) + 1)
  return [...count].map(([c, n]) => `${n} ${c.toLowerCase()}`).join(' + ')
}

function Dots({ colors, small }: { colors: string[]; small?: boolean }) {
  return (
    <span className="dots">
      {colors.map((c, i) => (
        <i key={i} className={`dot ${small ? 'sm' : ''} ${colorClass(c)}`} title={c} />
      ))}
    </span>
  )
}

/** La ficha de una carta, ordenada como la lee un jugador: si se puede jugar, sus números, sus datos, qué hace
 *  (con la errata aplicada) y cómo se resuelve (Q&A). A la izquierda, la carta física: imagen, impresiones,
 *  tus copias y su precio. */
export default function CardModal({ id, skills, onClose, onFilter, children, onOpenPrint, onPrev, onNext }: Props) {
  const [card, setCard] = useState<CardDetail | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [side, setSide] = useState<'front' | 'back'>('front')
  const [printed, setPrinted] = useState(false)
  const [copied, setCopied] = useState(false)

  // El componente se monta con key={id}, así que el estado arranca limpio para cada carta
  useEffect(() => {
    api.card(id).then(setCard).catch((e: Error) => setError(e.message))
  }, [id])

  // Abierta la carta, la dirección lleva su número (?card=BT20-149), también si se abrió por id.
  useEffect(() => {
    if (card && new URLSearchParams(window.location.search).has('card')) showCardRef(card.ref)
  }, [card])

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose()
      // ← → para pasar de carta, salvo escribiendo (una nota, un selector…).
      const target = e.target as HTMLElement
      if (target.closest('input, textarea, select, [contenteditable]')) return
      if (e.key === 'ArrowLeft' && onPrev) onPrev()
      if (e.key === 'ArrowRight' && onNext) onNext()
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [onClose, onPrev, onNext])

  const back = side === 'back' && !!card?.has_back
  const name = card ? (back ? card.back_name : card.name) : ''
  const deckRules = card ? card.keyword_skills.map((s) => skills.deckRule(s)).filter(Boolean) : []
  const isLeader = card?.card_type === 'LEADER'
  const text = card ? (back ? card.back_text : card.errata ? errataText(card.text, card.errata.before, card.errata.after, printed) : card.text) : ''

  const copyText = async () => {
    if (!card) return
    const plain = (back ? card.back_text : card.errata ? errataText(card.text, card.errata.before, card.errata.after).replace(/⟦\+([^⟧]*)⟧/g, '$1') : card.text)
      .replace(/<br\s*\/?>/gi, '\n')
      .replace(/<[^>]+>/g, '')
    try {
      await navigator.clipboard.writeText(plain)
      setCopied(true)
      window.setTimeout(() => setCopied(false), 1800)
    } catch {
      /* sin portapapeles: el texto se puede seleccionar a mano */
    }
  }

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal card-detail" role="dialog" aria-modal="true" aria-label={name || 'Card'} onClick={(e) => e.stopPropagation()}>
        {/* Móvil: barra fija con el nombre, ‹ › y cerrar */}
        <div className="cd-topbar">
          <button className="icon-btn" onClick={onPrev} disabled={!onPrev} aria-label="Previous card">
            ‹
          </button>
          <span className="cd-topbar-name">{name}</span>
          <button className="icon-btn" onClick={onNext} disabled={!onNext} aria-label="Next card">
            ›
          </button>
          <button className="icon-btn" onClick={onClose} aria-label="Close">
            ✕
          </button>
        </div>
        <button className="icon-btn close cd-close" onClick={onClose} aria-label="Close">
          ✕
        </button>
        {onPrev && (
          <button className="cd-nav prev" onClick={onPrev} aria-label="Previous card" title="Previous card (←)">
            ‹
          </button>
        )}
        {onNext && (
          <button className="cd-nav next" onClick={onNext} aria-label="Next card" title="Next card (→)">
            ›
          </button>
        )}
        {error && <p className="error">{error}</p>}
        {!card && !error && <p className="muted cd-loading">Loading…</p>}
        {card && (
          <div className="cd-layout">
            <aside className="cd-art">
              <div className="cd-art-top">
                {card.has_back && (
                  <div className="cd-face" role="group" aria-label="Side">
                    <button className={side === 'front' ? 'on' : ''} onClick={() => setSide('front')} aria-pressed={side === 'front'}>
                      Front
                    </button>
                    <button className={side === 'back' ? 'on' : ''} onClick={() => setSide('back')} aria-pressed={side === 'back'}>
                      {isLeader ? 'Awaken' : 'Back'}
                    </button>
                  </div>
                )}
                <img className="cd-img" src={back ? card.back_image_url : card.image_url} alt={name} referrerPolicy="no-referrer" />
                {card.prints.length > 1 && (
                  <section className="card-prints">
                    <span className="cd-label">Printings of {card.card_number}</span>
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
              </div>
              {children && <div className="cd-owned">{children}</div>}
              {card.price && (
                <div className="cd-price">
                  <PriceBox price={card.price} />
                  {card.price.counts && <PriceChart points={card.price_history ?? []} />}
                </div>
              )}
            </aside>

            <div className="cd-info">
              <header className="cd-head">
                <h2>{name}</h2>
                <p className="cd-meta">
                  <b>{card.card_number}</b> · {card.card_set}
                </p>
                <div className="cd-badges">
                  {card.rarity && (
                    <span className="cd-badge rarity">
                      {card.rarity}
                      {card.rarity_code && ` · ${card.rarity_code}`}
                    </span>
                  )}
                  <span className="cd-badge">{card.errata ? '✎ Errata' : 'Errata: none'}</span>
                  <span className="cd-badge">Q&amp;A: {card.rulings.length}</span>
                  <CopyLink cardRef={card.ref} />
                </div>
              </header>

              <Status card={card} deckRules={deckRules as string[]} />

              <div className="cd-stats" aria-label="Card numbers">
                <div>
                  <span className="cd-label">{card.card_type.startsWith('Z-') ? 'Z-Energy' : 'Cost'}</span>
                  <b>
                    {card.card_type.startsWith('Z-') ? (card.z_energy_cost ?? '—') : (card.energy ?? '—')}
                    {card.color_cost_colors.length > 0 && <Dots colors={card.color_cost_colors} />}
                  </b>
                  <small>{card.color_cost_colors.length ? colorCostText(card.color_cost_colors) : isLeader ? 'Leader' : 'no colour cost'}</small>
                </div>
                <div>
                  <span className="cd-label">Power</span>
                  <b>{(back ? card.back_power : card.power)?.toLocaleString('en-GB') ?? '—'}</b>
                  <small>{back ? 'awakened' : card.has_back ? 'front side' : ' '}</small>
                </div>
                <div>
                  <span className="cd-label">Combo</span>
                  <b>{card.combo_power != null ? `+${card.combo_power.toLocaleString('en-GB')}` : '—'}</b>
                  <small>{card.combo_energy != null ? `costs ${card.combo_energy} energy` : "can't combo"}</small>
                </div>
              </div>

              <div className="cd-tiles">
                <div>
                  <span className="cd-label">Type</span>
                  <button className="cd-tile-value" onClick={() => onFilter('type', card.card_type)} title="Filter by this type">
                    {typeLabel(card.card_type)}
                  </button>
                </div>
                <div>
                  <span className="cd-label">Color</span>
                  <span className="cd-tile-value">
                    <Dots colors={card.colors} small /> {card.colors.join(' / ')}
                  </span>
                </div>
                <div>
                  <span className="cd-label">Rarity</span>
                  <span className="cd-tile-value">{card.rarity || '—'}</span>
                </div>
                <TileList label="Character" values={card.characters} onPick={(v) => onFilter('character', v)} />
                <TileList label="Special trait" values={card.special_traits} onPick={(v) => onFilter('special_trait', v)} />
                <TileList label="Era" values={card.eras} onPick={(v) => onFilter('era', v)} />
              </div>

              <section>
                <div className="cd-section-head">
                  <span className="cd-label">Card text{back ? ' · Awaken side' : ''}</span>
                  <button type="button" className="btn small ghost" onClick={copyText}>
                    {copied ? 'Copied ✓' : '⧉ Copy text'}
                  </button>
                </div>
                {card.errata && !back && (
                  <div className="cd-errata">
                    <span aria-hidden>✎</span>
                    <span>
                      <b>Errata{card.errata.date && ` (${card.errata.date})`}</b> — this is the current wording; the change is
                      highlighted.{' '}
                      <button type="button" className="link" onClick={() => setPrinted(!printed)}>
                        {printed ? 'Show current text' : 'Show printed text'}
                      </button>
                      {card.errata.notes && <small>{card.errata.notes}</small>}
                    </span>
                  </div>
                )}
                <CardText text={text} skills={skills} onKeyword={(kw) => onFilter('keyword', kw)} />
              </section>

              <section>
                <div className="cd-section-head">
                  <span className="cd-label">Official Q&amp;A · {card.rulings.length}</span>
                </div>
                {card.rulings.length ? (
                  <div className="cd-qa">
                    {card.rulings.map((r, i) => (
                      <details key={r.order} open={i < 2}>
                        <summary>
                          {r.question}
                          {r.is_new && <span className="qa-new">new</span>}
                        </summary>
                        <p className="cd-answer">{r.answer}</p>
                        {r.set_label && <small>{r.set_label}</small>}
                      </details>
                    ))}
                  </div>
                ) : (
                  <p className="muted small cd-empty">No official questions for this card yet.</p>
                )}
              </section>
              {card.notes && <p className="muted small">Notes: {card.notes.split('|').pop()?.replace(/<br\s*\/?>/gi, ' · ')}</p>}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

/** ¿Se puede jugar? Banned / Limited / límites de construcción (Ultimate…) o legal, y en qué formatos. */
function Status({ card, deckRules }: { card: CardDetail; deckRules: string[] }) {
  const formats = card.regulations.join(' · ')
  if (card.legality === 'banned') {
    return (
      <div className="cd-status banned">
        <span aria-hidden>⛔</span>
        <div>
          <strong>Banned in official tournaments</strong>
          <span>It can't be in the deck or the side deck.{card.legality_since && ` ${card.legality_since}`}</span>
        </div>
      </div>
    )
  }
  if (card.legality === 'limited' || deckRules.length) {
    return (
      <div className="cd-status limit">
        <span aria-hidden>⚠</span>
        <div>
          <strong>{[card.legality === 'limited' && 'Limited · 1 copy max (deck + side deck)', ...deckRules].filter(Boolean).join(' · ')}</strong>
          <span>
            {formats && `Legal in ${formats}`}
            {card.legality === 'limited' && card.legality_since && ` · ${card.legality_since}`}
          </span>
        </div>
      </div>
    )
  }
  return (
    <div className="cd-status ok">
      <span aria-hidden>✓</span>
      <div>
        <strong>Legal · up to 4 copies</strong>
        {formats && <span>{formats}</span>}
      </div>
    </div>
  )
}

/** Baldosa con uno o varios valores que filtran la búsqueda al pulsarlos. */
function TileList({ label, values, onPick }: { label: string; values: string[]; onPick: (v: string) => void }) {
  return (
    <div>
      <span className="cd-label">{label}</span>
      <span className="cd-tile-value">
        {values.length
          ? values.map((v, i) => (
              <span key={v}>
                {i > 0 && ' / '}
                <button className="cd-tile-link" onClick={() => onPick(v)} title={`Filter by ${v}`}>
                  {v}
                </button>
              </span>
            ))
          : '—'}
      </span>
    </div>
  )
}

const SOURCE_LABEL = { cardmarket: 'Cardmarket', tcgplayer: 'TCGplayer', manual: 'set by hand' } as const

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
 * las ofertas en España y Europa (Cardmarket) y en TCGplayer. Su evolución va debajo (PriceChart). */
function PriceBox({ price }: { price: CardPrice }) {
  const what = price.manual
    ? 'price set by hand'
    : price.suspect && !price.counts
      ? 'doubtful price: a single listing, no sales (not counted in the value)'
      : !price.counts
        ? "only a seller's asking price: no sales (not counted in the value)"
        : `market price · ${SOURCE_LABEL[price.source]}`
  const sources = [
    price.cardmarket_eur != null && `Cardmarket ${formatEur(price.cardmarket_eur)}`,
    price.tcgplayer_eur != null && `TCGplayer ${formatEur(price.tcgplayer_eur)} (US)`,
    price.low != null && `from ${formatEur(price.low)} in Europe`,
  ].filter(Boolean)
  return (
    <div className={`price-box ${price.counts ? '' : 'is-low'}`}>
      <span className="price-main">{priceLabel(price)}</span>
      <span className="price-what small">{what}</span>
      {!price.manual && sources.length > 0 && <span className="price-details muted small">{sources.join(' · ')}</span>}
      {(price.change_7 != null || price.change_30 != null) && (
        <span className="price-changes small">
          <Change label="7 days" value={price.change_7} />
          <Change label="30 days" value={price.change_30} />
        </span>
      )}
      <span className="price-links small">
        <a href={price.url_es} target="_blank" rel="noreferrer">Offers in Spain ↗</a>
        <a href={price.url} target="_blank" rel="noreferrer">Offers in Europe ↗</a>
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
    <button type="button" className="cd-badge link copy-link" onClick={copy} title={link}>
      {state === 'copied' ? 'Link copied ✓' : '🔗 Copy link'}
    </button>
  )
}
