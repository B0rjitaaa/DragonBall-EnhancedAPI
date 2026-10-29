import { useEffect, useState } from 'react'
import CardModal from './components/CardModal'
import { useOpenCard } from './lib/cardLink'
import { api } from './lib/api'
import { formatEur, priceLabel } from './lib/prices'
import { SkillIndex } from './lib/skills'
import type { PricePoint, RadarCard, RadarResponse } from './lib/types'
import { cardThumb } from './lib/types'

const PERIODS = [7, 30, 90] as const
const dateFormat = new Intl.DateTimeFormat('en-GB', { day: 'numeric', month: 'long', year: 'numeric' })
const shortDate = new Intl.DateTimeFormat('en-GB', { day: 'numeric', month: 'short' })

const pct = (change: number) => `${change > 0 ? '▲' : '▼'} ${Math.abs(Math.round(change * 100))} %`

/** Precios: lo que vale tu colección y cómo ha cambiado, lo que más sube y baja en 7, 30 o 90 días y lo
 * más caro; de tu colección o de todo el catálogo. */
export default function PricesPage() {
  const [days, setDays] = useState<number>(30)
  const [scope, setScope] = useState<'collection' | 'all'>('collection')
  const [data, setData] = useState<RadarResponse | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [openId, setOpenId] = useOpenCard()
  const [skills, setSkills] = useState<SkillIndex>(SkillIndex.empty)

  useEffect(() => {
    api.keywordSkills().then((d) => setSkills(new SkillIndex(d))).catch(() => {})
  }, [])

  useEffect(() => {
    api
      .priceRadar(days, scope)
      .then((d) => {
        setData(d)
        setError(null)
      })
      .catch((e: Error) => setError(e.message))
  }, [days, scope])

  // El historial empieza el día que se activaron los precios: antes de N días no hay con qué comparar.
  const young = data?.since != null && Date.now() - Date.parse(data.since) < days * 86_400_000
  const mine = scope === 'collection'

  return (
    <main className="prices-page">
      <header className="prices-head">
        <div>
          <h1>Prices</h1>
          <p className="muted">
            Cardmarket (Europe) checked against TCGplayer (US), every day. No fake copies or cards without sales.
          </p>
        </div>
        <div className="prices-controls">
          <div className="segmented" role="group" aria-label="Which cards">
            <button className={mine ? 'on' : ''} onClick={() => setScope('collection')}>My collection</button>
            <button className={!mine ? 'on' : ''} onClick={() => setScope('all')}>Whole catalogue</button>
          </div>
          <div className="segmented" role="group" aria-label="Period">
            {PERIODS.map((p) => (
              <button key={p} className={days === p ? 'on' : ''} onClick={() => setDays(p)}>{p} days</button>
            ))}
          </div>
        </div>
      </header>

      {error && <p className="error">{error}</p>}
      {!data && !error && <p className="muted">Loading…</p>}

      {data?.value && (
        <section className="value-hero">
          <div className="value-figures">
            <span className="muted small">Your collection is worth</span>
            <strong className="value-now">{formatEur(data.value.now)}</strong>
            {data.value.change != null && Math.round(data.value.change * 100) !== 0 && (
              <span className={`value-change ${data.value.change > 0 ? 'up' : 'down'}`}>
                {pct(data.value.change)} <small className="muted">in {days} days</small>
              </span>
            )}
          </div>
          <ValueChart series={data.value.series} />
        </section>
      )}

      {data && (young || data.basis === 'cardmarket') && (
        <p className="prices-note">
          {data.since ? `Price history started on ${dateFormat.format(new Date(data.since))}. ` : ''}
          Until there are {days} days of our own history, rises and falls compare today's price with its{' '}
          <strong>average sale price over the last {days === 7 ? 7 : 30} days on Cardmarket</strong>.
        </p>
      )}

      {data && (
        <>
          <Tiles title={`Up in ${days} days`} cards={data.risers} empty="Nothing went up in this period." onOpen={setOpenId} />
          <Tiles title={`Down in ${days} days`} cards={data.fallers} empty="Nothing went down in this period." onOpen={setOpenId} />
          <Tiles title={mine ? 'Most valuable in your collection' : 'Most valuable'} cards={data.expensive}
            empty="No prices yet." onOpen={setOpenId} />
        </>
      )}

      {openId !== null && (
        <CardModal
          key={openId}
          id={openId}
          onOpenPrint={setOpenId}
          skills={skills}
          onClose={() => setOpenId(null)}
          onFilter={(field, value) => {
            window.location.href = `/?add=${encodeURIComponent(field)}&value=${encodeURIComponent(value)}`
          }}
        />
      )}
    </main>
  )
}

/** Fichas con la carta, su precio y cuánto ha cambiado. */
function Tiles({ title, cards, empty, onOpen }: { title: string; cards: RadarCard[]; empty: string; onOpen: (id: number) => void }) {
  return (
    <section className="prices-section">
      <h2>{title}</h2>
      {cards.length === 0 ? (
        <p className="muted small">{empty}</p>
      ) : (
        <ol className="price-tiles">
          {cards.map((c) => (
            <li key={c.id}>
              <button className="price-tile" onClick={() => onOpen(c.id)} title={`${c.card_number} · ${c.name}`}>
                <span className="price-tile-img">
                  <img src={cardThumb(c)} alt="" loading="lazy" referrerPolicy="no-referrer" />
                  {c.change != null && <span className={`price-badge ${c.change > 0 ? 'up' : 'down'}`}>{pct(c.change)}</span>}
                </span>
                <span className="price-tile-name">{c.name}</span>
                <span className="price-tile-meta muted">{c.card_number} · {c.rarity_code}</span>
                <span className="price-tile-price">
                  <strong>{c.price ? priceLabel(c.price) : '—'}</strong>
                  {c.before != null && <small className="muted"> was {formatEur(c.before)}</small>}
                </span>
              </button>
            </li>
          ))}
        </ol>
      )}
    </section>
  )
}

/** Valor de la colección día a día (área), con el mínimo y el máximo del periodo. */
function ValueChart({ series }: { series: PricePoint[] }) {
  const W = 600
  const H = 140
  const pad = { top: 6, right: 2, bottom: 2, left: 2 }
  const values = series.map((p) => p.eur).filter((v) => v > 0)
  if (values.length < 2) return <p className="muted small value-empty">The chart will appear once there are a few days of history.</p>
  const min = Math.min(...values)
  const max = Math.max(...values)
  const firstIdx = series.findIndex((p) => p.eur > 0)
  const shown = series.slice(firstIdx)
  const x = (i: number) => pad.left + (i / (shown.length - 1)) * (W - pad.left - pad.right)
  const y = (v: number) => pad.top + (max === min ? 0.5 : 1 - (v - min) / (max - min)) * (H - pad.top - pad.bottom)
  const line = shown.map((p, i) => `${i ? 'L' : 'M'}${x(i)},${y(p.eur)}`).join(' ')
  return (
    <figure className="value-chart">
      <svg viewBox={`0 0 ${W} ${H}`} preserveAspectRatio="none" role="img"
        aria-label={`Collection value: from ${formatEur(shown[0].eur)} to ${formatEur(shown[shown.length - 1].eur)}`}>
        <defs>
          <linearGradient id="value-fill" x1="0" x2="0" y1="0" y2="1">
            <stop offset="0" stopColor="currentColor" stopOpacity="0.35" />
            <stop offset="1" stopColor="currentColor" stopOpacity="0" />
          </linearGradient>
        </defs>
        <path d={`${line} V${H - pad.bottom} H${x(0)} Z`} fill="url(#value-fill)" />
        <path d={line} fill="none" stroke="currentColor" strokeWidth="2" vectorEffect="non-scaling-stroke" />
      </svg>
      <figcaption className="muted small">
        <span>{shortDate.format(new Date(shown[0].date))}</span>
        <span>min {formatEur(min)} · max {formatEur(max)}</span>
        <span>today</span>
      </figcaption>
    </figure>
  )
}
