// Locations → Decks → Stats: cómo te va con tus mazos según las partidas anotadas. Resumen arriba, una fila por mazo,
// enfrentamientos con los Leaders rivales y la evolución semana a semana. Con pocas partidas, los porcentajes se
// enseñan atenuados («few games») y siempre con cuántas partidas son.
import { useEffect, useMemo, useState } from 'react'
import { api } from '../lib/api'
import type { DeckStatsData, StatsOpponent } from '../lib/types'
import { cardThumb } from '../lib/types'

const PERIODS: [number | null, string][] = [[30, 'Last 30 days'], [90, 'Last 3 months'], [null, 'All time']]
type SortKey = 'name' | 'played' | 'win_rate' | 'last_played'

const pct = (rate: number | null) => (rate == null ? '—' : `${Math.round(rate * 100)}%`)
const rateOf = (wins: number, played: number) => (played ? wins / played : null)

function ago(iso: string) {
  const days = Math.round((Date.now() - new Date(`${iso}T12:00:00`).getTime()) / 86400000)
  return days <= 0 ? 'today' : days === 1 ? 'yesterday' : days < 30 ? `${days} days ago` : new Date(iso).toLocaleDateString('en-GB', { day: 'numeric', month: 'short' })
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

  useEffect(() => {
    const ctrl = new AbortController()
    api
      .deckStats(days, archived, ctrl.signal)
      .then((d) => {
        setData(d)
        setError('')
      })
      .catch((e: Error) => e.name !== 'AbortError' && setError(e.message))
    return () => ctrl.abort()
  }, [days, archived])

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
            <h3 className="loc-sub">By deck</h3>
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
                    <tr key={d.deck_id} className={few(d.played) ? 'few' : ''}>
                      <td>
                        <a className="stats-deck" href={`/collection/deck/${d.uid}`}>
                          {d.leader ? <img src={d.leader.image} alt="" loading="lazy" referrerPolicy="no-referrer" /> : <span className="locdeck-thumb-empty" />}
                          <span>
                            {d.name}
                            {d.status === 'parked' && <small className="muted"> · archived</small>}
                          </span>
                        </a>
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
                        <span className="stats-last5" aria-label={d.last5.join(', ')}>
                          {d.last5.map((r, i) => (
                            <i key={i} className={r} title={r} />
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
                    {data.decks.map((d) => (
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
              <h3 className="loc-sub">Over time</h3>
              <WeeksChart weeks={data.weeks} />
            </section>
          </div>
        </>
      )}
    </div>
  )
}

/** Partidas por semana (barras: victorias en verde sobre el total) y el porcentaje de victorias (línea). */
function WeeksChart({ weeks }: { weeks: DeckStatsData['weeks'] }) {
  if (weeks.length === 0) return null
  const W = 560
  const H = 200
  const pad = { l: 28, r: 34, t: 12, b: 26 }
  const max = Math.max(1, ...weeks.map((w) => w.played))
  const slot = (W - pad.l - pad.r) / weeks.length
  const bw = Math.min(42, slot * 0.6)
  const y = (n: number) => pad.t + (H - pad.t - pad.b) * (1 - n / max)
  const yr = (r: number) => pad.t + (H - pad.t - pad.b) * (1 - r)
  const x = (i: number) => pad.l + slot * i + slot / 2
  const line = weeks.map((w, i) => `${i ? 'L' : 'M'}${x(i).toFixed(1)},${yr(w.wins / w.played).toFixed(1)}`).join(' ')
  const label = (iso: string) => new Date(`${iso}T12:00:00`).toLocaleDateString('en-GB', { day: 'numeric', month: 'short' })
  return (
    <div className="stats-chart">
      <svg viewBox={`0 0 ${W} ${H}`} role="img" aria-label="Matches per week and win rate">
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
        {weeks.map((w, i) => (
          <g key={w.week}>
            <title>{`Week of ${label(w.week)}: ${w.played} matches, ${w.wins} won`}</title>
            <rect x={x(i) - bw / 2} y={y(w.played)} width={bw} height={y(0) - y(w.played)} className="bar-all" rx="3" />
            <rect x={x(i) - bw / 2} y={y(w.wins)} width={bw} height={y(0) - y(w.wins)} className="bar-win" rx="3" />
            {(weeks.length <= 12 || i % Math.ceil(weeks.length / 12) === 0) && (
              <text x={x(i)} y={H - 8} className="axis" textAnchor="middle">
                {label(w.week)}
              </text>
            )}
          </g>
        ))}
        <path d={line} className="rate-line" />
        {weeks.map((w, i) => (
          <circle key={w.week} cx={x(i)} cy={yr(w.wins / w.played)} r="3.5" className="rate-dot" />
        ))}
      </svg>
      <p className="muted small stats-legend">
        <i className="lg-all" /> matches <i className="lg-win" /> won <i className="lg-line" /> win rate
      </p>
    </div>
  )
}
