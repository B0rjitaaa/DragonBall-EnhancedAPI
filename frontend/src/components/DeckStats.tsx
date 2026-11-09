// Locations → Decks → Stats: cómo te va con tus mazos según las partidas anotadas. Resumen arriba, una fila por mazo,
// enfrentamientos con los Leaders rivales y la evolución semana a semana. Con pocas partidas, los porcentajes se
// enseñan atenuados («few games») y siempre con cuántas partidas son. Al pulsar mazos en «By deck» el resto (resumen,
// enfrentamientos y gráfica) se calcula solo con esos.
import { useEffect, useMemo, useState, type ReactNode } from 'react'
import { api } from '../lib/api'
import type { DeckStatsData, StatsDayDeck, StatsGame, StatsOpponent } from '../lib/types'
import { cardThumb } from '../lib/types'

const PERIODS: [number | null, string][] = [[30, 'Last 30 days'], [90, 'Last 3 months'], [null, 'All time']]
type SortKey = 'name' | 'played' | 'win_rate' | 'last_played'

const pct = (rate: number | null) => (rate == null ? '—' : `${Math.round(rate * 100)}%`)
const rateOf = (wins: number, played: number) => (played ? wins / played : null)

function ago(iso: string) {
  const days = Math.round((Date.now() - new Date(`${iso}T12:00:00`).getTime()) / 86400000)
  return days <= 0 ? 'today' : days === 1 ? 'yesterday' : days < 30 ? `${days} days ago` : new Date(iso).toLocaleDateString('en-GB', { day: 'numeric', month: 'short' })
}

const longDate = (iso: string) => new Date(`${iso}T12:00:00`).toLocaleDateString('en-GB', { weekday: 'short', day: 'numeric', month: 'short' })
const RESULT = { win: 'Win', loss: 'Loss', draw: 'Draw' } as const

/** Leyenda flotante propia (la del navegador tarda en salir): sigue al ratón y no se sale de la pantalla. */
type Tip = { x: number; y: number; body: ReactNode } | null
function Tooltip({ tip }: { tip: Tip }) {
  if (!tip) return null
  const left = tip.x > window.innerWidth - 280
  return (
    <div className="stats-tip" style={{ top: tip.y + 14, ...(left ? { right: window.innerWidth - tip.x + 12 } : { left: tip.x + 12 }) }}>
      {tip.body}
    </div>
  )
}
function tipHandlers(setTip: (t: Tip) => void, body: () => ReactNode) {
  return {
    onMouseEnter: (e: React.MouseEvent) => setTip({ x: e.clientX, y: e.clientY, body: body() }),
    onMouseMove: (e: React.MouseEvent) => setTip({ x: e.clientX, y: e.clientY, body: body() }),
    onMouseLeave: () => setTip(null),
  }
}

/** Color de un porcentaje de victorias: rojo (0%) → ámbar (50%) → verde (100%). */
function heat(rate: number | null) {
  if (rate == null) return undefined
  const hue = Math.round(rate * 130)
  return `hsl(${hue} 65% 42% / 0.55)`
}

export default function DeckStats() {
  const [days, setDays] = useState<number | null>(null)
  const [archived, setArchived] = useState(false)
  const [data, setData] = useState<DeckStatsData | null>(null)
  const [error, setError] = useState('')
  const [sort, setSort] = useState<{ key: SortKey; desc: boolean }>({ key: 'played', desc: true })
  const [selected, setSelected] = useState<number[]>([])
  const [tip, setTip] = useState<Tip>(null)

  useEffect(() => {
    const ctrl = new AbortController()
    api
      .deckStats(days, archived, selected, ctrl.signal)
      .then((d) => {
        setData(d)
        setError('')
        // Si al cambiar el periodo un mazo elegido se queda sin partidas, deja de estar elegido.
        const present = selected.filter((id) => d.decks.some((x) => x.deck_id === id))
        if (present.length !== selected.length) setSelected(present)
      })
      .catch((e: Error) => e.name !== 'AbortError' && setError(e.message))
    return () => ctrl.abort()
  }, [days, archived, selected])

  const toggle = (id: number) => setSelected((s) => (s.includes(id) ? s.filter((x) => x !== id) : [...s, id]))

  const decks = useMemo(() => {
    const list = [...(data?.decks ?? [])]
    const val = (d: DeckStatsData['decks'][number]) =>
      sort.key === 'name' ? d.name.toLowerCase() : sort.key === 'played' ? d.played : sort.key === 'win_rate' ? (d.win_rate ?? -1) : d.last_played
    list.sort((a, b) => {
      const x = val(a)
      const y = val(b)
      const c = x < y ? -1 : x > y ? 1 : 0
      return sort.desc ? -c : c
    })
    return list
  }, [data, sort])

  if (error) return <p className="error small">{error}</p>
  if (!data) return <p className="muted small">Loading the stats…</p>
  const t = data.totals
  const low = data.low_sample
  const few = (n: number) => n < low
  const head = (key: SortKey, label: string, cls = '') => (
    <th className={cls}>
      <button className="stats-sort" onClick={() => setSort((s) => ({ key, desc: s.key === key ? !s.desc : key !== 'name' }))}>
        {label} {sort.key === key ? (sort.desc ? '▾' : '▴') : ''}
      </button>
    </th>
  )
  const oppName = (o: StatsOpponent) => {
    const card = o.leader_bandai_id ? data.catalog[o.leader_bandai_id] : null
    return card ? `${card.name}` : o.name || 'Unknown'
  }
  const gameTip = (g: StatsGame) => () => {
    const card = g.opponent_leader_bandai_id ? data.catalog[g.opponent_leader_bandai_id] : null
    return (
      <div className="stats-tip-game">
        {card && <img src={cardThumb(card)} alt="" referrerPolicy="no-referrer" />}
        <div>
          <b className={`res-${g.result}`}>{RESULT[g.result]}</b> vs <b>{card?.name ?? (g.opponent || 'Unknown')}</b>
          <div className="muted small">
            {longDate(g.played_on)}
            {g.went_first != null && ` · going ${g.went_first ? 'first' : 'second'}`}
          </div>
        </div>
      </div>
    )
  }
  const chosen = data.decks.filter((d) => selected.includes(d.deck_id))
  const matrixDecks = selected.length ? data.decks.filter((d) => selected.includes(d.deck_id)) : data.decks

  return (
    <div className="deck-stats-panel">
      <div className="stats-filters">
        <span className="segmented" role="group" aria-label="Period">
          {PERIODS.map(([d, label]) => (
            <button key={label} className={days === d ? 'on' : ''} onClick={() => setDays(d)}>
              {label}
            </button>
          ))}
        </span>
        <label className="small">
          <input type="checkbox" checked={archived} onChange={(e) => setArchived(e.target.checked)} /> Include archived decks
        </label>
        {chosen.length > 0 && (
          <span className="stats-showing">
            Showing:
            {chosen.map((d) => (
              <button key={d.deck_id} className="stats-chip" onClick={() => toggle(d.deck_id)} title="Remove from the filter">
                {d.name} ✕
              </button>
            ))}
            <button className="link small" onClick={() => setSelected([])}>
              Clear
            </button>
          </span>
        )}
      </div>

      {t.played === 0 ? (
        <p className="empty">No matches recorded {days ? 'in this period' : 'yet'}. Add them from a deck with “+ Result”.</p>
      ) : (
        <>
          <div className="stats-kpis">
            <div className="stats-kpi">
              <strong>{t.played}</strong>
              <span>matches</span>
            </div>
            <div className={`stats-kpi ${few(t.played) ? 'few' : ''}`}>
              <strong>{pct(t.win_rate)}</strong>
              <span>
                win rate · {t.wins}-{t.losses}-{t.draws}
              </span>
            </div>
            <div className={`stats-kpi streak-${t.streak.result ?? 'none'}`}>
              <strong>
                {t.streak.result === 'win' ? 'W' : t.streak.result === 'loss' ? 'L' : 'D'}
                {t.streak.count}
              </strong>
              <span>current streak</span>
            </div>
            <div className="stats-kpi">
              <strong className="stats-split">
                <span title={`${t.first.wins} of ${t.first.played}`}>1st {pct(rateOf(t.first.wins, t.first.played))}</span>
                <span title={`${t.second.wins} of ${t.second.played}`}>2nd {pct(rateOf(t.second.wins, t.second.played))}</span>
              </strong>
              <span>
                going first ({t.first.played}) / second ({t.second.played})
              </span>
            </div>
            <div className="stats-kpi">
              <strong className="stats-text">{data.best_deck?.name ?? '—'}</strong>
              <span>
                best deck{data.best_deck && ` · ${pct(data.best_deck.win_rate)} in ${data.best_deck.played}`}
              </span>
            </div>
            <div className="stats-kpi">
              <strong className="stats-text">{data.toughest[0] ? oppName(data.toughest[0]) : '—'}</strong>
              <span>
                toughest opponent
                {data.toughest[0] && ` · ${pct(data.toughest[0].win_rate)} in ${data.toughest[0].played}`}
              </span>
            </div>
          </div>

          <section className="stats-block">
            <h3 className="loc-sub">
              By deck <span className="muted stats-hint">· click decks to filter the stats</span>
            </h3>
            <div className="stats-table-wrap">
              <table className="stats-table">
                <thead>
                  <tr>
                    {head('name', 'Deck')}
                    {head('played', '#', 'num')}
                    <th className="num">W-L-D</th>
                    {head('win_rate', 'Win rate')}
                    <th title="Oldest to newest">Last 5</th>
                    <th className="hide-narrow">1st / 2nd</th>
                    {head('last_played', 'Last played', 'hide-narrow')}
                  </tr>
                </thead>
                <tbody>
                  {decks.map((d) => (
                    <tr
                      key={d.deck_id}
                      className={`stats-pick ${few(d.played) ? 'few' : ''} ${selected.includes(d.deck_id) ? 'sel' : selected.length ? 'dim' : ''}`}
                      onClick={() => toggle(d.deck_id)}
                      aria-selected={selected.includes(d.deck_id)}
                    >
                      <td>
                        <span className="stats-deck">
                          {d.leader ? <img src={d.leader.image} alt="" loading="lazy" referrerPolicy="no-referrer" /> : <span className="locdeck-thumb-empty" />}
                          <span>
                            <a href={`/collection/deck/${d.uid}`} onClick={(e) => e.stopPropagation()} title="Open the deck">
                              {d.name}
                            </a>
                            {d.status === 'parked' && <small className="muted"> · archived</small>}
                          </span>
                        </span>
                      </td>
                      <td className="num">{d.played}</td>
                      <td className="num">
                        {d.wins}-{d.losses}-{d.draws}
                      </td>
                      <td>
                        <span className="stats-bar">
                          <i style={{ width: `${(d.win_rate ?? 0) * 100}%`, background: heat(d.win_rate) }} />
                        </span>
                        <span className="stats-rate">
                          {pct(d.win_rate)}
                          {few(d.played) && <small className="muted"> · few games</small>}
                        </span>
                      </td>
                      <td>
                        <span className="stats-last5" aria-label={d.last5.map((g) => `${g.result} vs ${g.opponent}`).join(', ')}>
                          {d.last5.map((g, i) => (
                            <i key={i} className={g.result} {...tipHandlers(setTip, gameTip(g))} />
                          ))}
                        </span>
                      </td>
                      <td className="small hide-narrow">
                        {pct(rateOf(d.first.wins, d.first.played))} / {pct(rateOf(d.second.wins, d.second.played))}
                      </td>
                      <td className="small muted hide-narrow">{ago(d.last_played)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>

          <div className="stats-grid">
            <section className="stats-block">
              <h3 className="loc-sub">Matchups · my decks vs rival Leaders</h3>
              <div className="stats-table-wrap">
                <table className="stats-matrix">
                  <thead>
                    <tr>
                      <th />
                      {data.opponents.map((o) => {
                        const card = o.leader_bandai_id ? data.catalog[o.leader_bandai_id] : null
                        return (
                          <th key={o.key} title={`${oppName(o)} · ${o.played} matches`}>
                            {card ? <img src={cardThumb(card)} alt={card.name} loading="lazy" referrerPolicy="no-referrer" /> : <span className="stats-opp-text">{o.name}</span>}
                          </th>
                        )
                      })}
                    </tr>
                  </thead>
                  <tbody>
                    {matrixDecks.map((d) => (
                      <tr key={d.deck_id}>
                        <th className="stats-row-name">{d.name}</th>
                        {data.opponents.map((o) => {
                          const c = data.matchups[String(d.deck_id)]?.[o.key]
                          const rate = c ? rateOf(c.wins, c.played) : null
                          return (
                            <td key={o.key} style={{ background: heat(rate) }} title={c ? `${d.name} vs ${oppName(o)}: ${c.wins} of ${c.played}` : ''}>
                              {c ? (
                                <>
                                  <b>{pct(rate)}</b>
                                  <small>{c.played}</small>
                                </>
                              ) : (
                                <span className="muted">—</span>
                              )}
                            </td>
                          )
                        })}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              {data.toughest.length > 0 && (
                <>
                  <h4 className="stats-mini-title">Toughest opponents</h4>
                  <ul className="stats-tough">
                    {data.toughest.map((o) => (
                      <li key={o.key}>
                        <span>{oppName(o)}</span>
                        <span className="muted small">
                          {o.wins}-{o.played - o.wins} · {pct(o.win_rate)}
                        </span>
                      </li>
                    ))}
                  </ul>
                </>
              )}
            </section>

            <section className="stats-block">
              <TimeChart weeks={data.weeks} days={data.days} setTip={setTip} />
            </section>
          </div>
        </>
      )}
      <Tooltip tip={tip} />
    </div>
  )
}

/** Partidas en el tiempo (barras: victorias en verde sobre el total) y el porcentaje de victorias (línea). Por días si las
 *  partidas abarcan menos de un mes; por semanas (de lunes a domingo) si abarcan más. */
type Point = { key: string; label: string; title: string; played: number; wins: number; decks: StatsDayDeck[] }

function TimeChart({ weeks, days, setTip }: { weeks: DeckStatsData['weeks']; days: DeckStatsData['days']; setTip: (t: Tip) => void }) {
  if (days.length === 0) return null
  const day = (iso: string) => new Date(`${iso}T12:00:00`)
  const span = (day(days[days.length - 1].day).getTime() - day(days[0].day).getTime()) / 86400000
  const daily = span < 31
  const short = (d: Date) => d.toLocaleDateString('en-GB', { day: 'numeric', month: 'short' })
  const points: Point[] = daily
    ? days.map((d) => ({ key: d.day, label: short(day(d.day)), title: longDate(d.day), played: d.played, wins: d.wins, decks: d.decks }))
    : weeks.map((w) => {
        const end = new Date(day(w.week).getTime() + 6 * 86400000)
        return { key: w.week, label: short(day(w.week)), title: `Week of ${short(day(w.week))}–${short(end)}`, played: w.played, wins: w.wins, decks: w.decks }
      })
  return (
    <>
      <h3 className="loc-sub">Over time · per {daily ? 'day' : 'week'}</h3>
      <BarsChart points={points} setTip={setTip} />
    </>
  )
}

function pointTip(w: Point) {
  const draws = w.decks.reduce((n, d) => n + d.draws, 0)
  const losses = w.played - w.wins - draws
  return (
    <div className="stats-tip-point">
      <b>{w.title}</b>
      <div>
        {w.played} {w.played === 1 ? 'match' : 'matches'} · <span className="res-win">{w.wins} won</span> · <span className="res-loss">{losses} lost</span>
        {draws > 0 && ` · ${draws} drawn`} · <b>{pct(rateOf(w.wins, w.played))}</b>
      </div>
      {w.decks.length > 0 && (
        <ul>
          {w.decks.map((d) => (
            <li key={d.deck_id}>
              <span>{d.name}</span>
              <span className="muted">
                {d.wins}–{d.losses}
                {d.draws > 0 && `–${d.draws}`}
              </span>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}

function BarsChart({ points, setTip }: { points: Point[]; setTip: (t: Tip) => void }) {
  const [hover, setHover] = useState<string | null>(null)
  const W = 560
  const H = 200
  const pad = { l: 28, r: 34, t: 12, b: 26 }
  const max = Math.max(1, ...points.map((w) => w.played))
  const slot = (W - pad.l - pad.r) / points.length
  const bw = Math.min(42, slot * 0.6)
  const y = (n: number) => pad.t + (H - pad.t - pad.b) * (1 - n / max)
  const yr = (r: number) => pad.t + (H - pad.t - pad.b) * (1 - r)
  const x = (i: number) => pad.l + slot * i + slot / 2
  const line = points.map((w, i) => `${i ? 'L' : 'M'}${x(i).toFixed(1)},${yr(w.wins / w.played).toFixed(1)}`).join(' ')
  const every = Math.ceil(points.length / 12)
  return (
    <div className="stats-chart">
      <svg viewBox={`0 0 ${W} ${H}`} role="img" aria-label="Matches and win rate over time">
        {[0, 0.5, 1].map((r) => (
          <g key={r}>
            <line x1={pad.l} x2={W - pad.r} y1={yr(r)} y2={yr(r)} className="grid" />
            <text x={W - pad.r + 4} y={yr(r) + 4} className="axis">
              {Math.round(r * 100)}%
            </text>
          </g>
        ))}
        <text x={pad.l - 6} y={y(max) + 4} className="axis" textAnchor="end">
          {max}
        </text>
        {points.map((w, i) => (
          <g key={w.key} className={hover === w.key ? 'hover' : ''}>
            <rect x={x(i) - bw / 2} y={y(w.played)} width={bw} height={y(0) - y(w.played)} className="bar-hl" rx="3" />
            <rect x={x(i) - bw / 2} y={y(w.played)} width={bw} height={y(0) - y(w.played)} className="bar-all" rx="3" />
            <rect x={x(i) - bw / 2} y={y(w.wins)} width={bw} height={y(0) - y(w.wins)} className="bar-win" rx="3" />
            {i % every === 0 && (
              <text x={x(i)} y={H - 8} className="axis" textAnchor="middle">
                {w.label}
              </text>
            )}
          </g>
        ))}
        {points.length > 1 && <path d={line} className="rate-line" />}
        {points.map((w, i) => (
          <circle key={w.key} cx={x(i)} cy={yr(w.wins / w.played)} r={hover === w.key ? 5 : 3.5} className="rate-dot" />
        ))}
        {/* Zona de toda la columna para que la leyenda salga sin tener que acertar en la barra. */}
        {points.map((w, i) => {
          const h = tipHandlers(setTip, () => pointTip(w))
          return (
            <rect
              key={w.key}
              x={pad.l + slot * i}
              y={pad.t}
              width={slot}
              height={H - pad.t - pad.b}
              className="hit"
              onMouseEnter={(e) => {
                setHover(w.key)
                h.onMouseEnter(e)
              }}
              onMouseMove={h.onMouseMove}
              onMouseLeave={() => {
                setHover(null)
                h.onMouseLeave()
              }}
            />
          )
        })}
      </svg>
      <p className="muted small stats-legend">
        <i className="lg-all" /> matches <i className="lg-win" /> won <i className="lg-line" /> win rate
      </p>
    </div>
  )
}
