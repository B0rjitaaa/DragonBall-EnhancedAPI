import { useMemo, useState } from 'react'
import { formatEur } from '../lib/prices'
import type { PricePoint } from '../lib/types'

const W = 340
const H = 150
const PAD = { top: 12, right: 10, bottom: 22, left: 10 }
const DAY = 86_400_000
const PERIODS = [
  { days: 30, label: '30 días' },
  { days: 90, label: '90 días' },
  { days: 0, label: 'Todo' },
] as const
const dateFormat = new Intl.DateTimeFormat('es-ES', { day: 'numeric', month: 'short' })

/** Precio en una fecha: el último cambio hasta ese día (el historial solo guarda los cambios). */
function priceAt(points: PricePoint[], t: number): number | null {
  let value: number | null = null
  for (const p of points) {
    if (Date.parse(p.date) <= t) value = p.eur
    else break
  }
  return value
}

/** Evolución del precio de una carta, en escalones hasta hoy, con el periodo a elegir y el precio de
 * cada día al pasar el ratón. Va bajo la foto de la carta, en el detalle. */
export default function PriceChart({ points }: { points: PricePoint[] }) {
  const [period, setPeriod] = useState<number>(90)
  const [hover, setHover] = useState<number | null>(null)
  const end = useMemo(() => Date.now(), [])
  const first = points.length ? Date.parse(points[0].date) : end
  const start = period ? Math.max(first, end - period * DAY) : first
  const shown = useMemo(() => {
    const before = priceAt(points, start)
    const inside = points.filter((p) => Date.parse(p.date) > start)
    return before != null ? [{ date: new Date(start).toISOString().slice(0, 10), eur: before }, ...inside] : inside
  }, [points, start])

  if (points.length === 0) return null
  if (points.length === 1 || shown.length === 0) {
    return (
      <section className="price-chart">
        <header>
          <strong>Evolución del precio</strong>
        </header>
        <p className="muted small">
          El historial empezó el {dateFormat.format(new Date(points[0].date))}: la gráfica se irá llenando con los días.
        </p>
      </section>
    )
  }

  const values = shown.map((p) => p.eur)
  const min = Math.min(...values)
  const max = Math.max(...values)
  const span = end - start || DAY
  const x = (t: number) => PAD.left + ((t - start) / span) * (W - PAD.left - PAD.right)
  const y = (v: number) => PAD.top + (max === min ? 0.5 : 1 - (v - min) / (max - min)) * (H - PAD.top - PAD.bottom)
  let line = `M${x(start)},${y(shown[0].eur)}`
  for (const p of shown.slice(1)) line += ` H${x(Math.max(start, Date.parse(p.date)))} V${y(p.eur)}`
  line += ` H${x(end)}`
  const area = `${line} V${H - PAD.bottom} H${x(start)} Z`
  const last = shown[shown.length - 1].eur
  const change = shown[0].eur ? (last - shown[0].eur) / shown[0].eur : 0
  const hoverT = hover != null ? start + ((hover - PAD.left) / (W - PAD.left - PAD.right)) * span : null
  const hoverV = hoverT != null ? priceAt(points, hoverT) : null

  return (
    <section className="price-chart">
      <header>
        <strong>Evolución del precio</strong>
        <span className={`price-change ${change > 0.005 ? 'up' : change < -0.005 ? 'down' : 'flat'}`}>
          {change > 0.005 ? '▲' : change < -0.005 ? '▼' : '='} {Math.abs(Math.round(change * 100))} %
        </span>
      </header>
      <div className="seg">
        {PERIODS.map((p) => (
          <button key={p.days} className={period === p.days ? 'on' : ''} onClick={() => setPeriod(p.days)}>
            {p.label}
          </button>
        ))}
      </div>
      <svg
        viewBox={`0 0 ${W} ${H}`}
        role="img"
        aria-label={`Precio: de ${formatEur(shown[0].eur)} a ${formatEur(last)}`}
        onMouseMove={(e) => {
          const box = e.currentTarget.getBoundingClientRect()
          setHover(Math.min(W - PAD.right, Math.max(PAD.left, ((e.clientX - box.left) / box.width) * W)))
        }}
        onMouseLeave={() => setHover(null)}
      >
        <defs>
          <linearGradient id="price-fill" x1="0" x2="0" y1="0" y2="1">
            <stop offset="0" stopColor="currentColor" stopOpacity="0.35" />
            <stop offset="1" stopColor="currentColor" stopOpacity="0" />
          </linearGradient>
        </defs>
        <path d={area} fill="url(#price-fill)" />
        <path d={line} fill="none" stroke="currentColor" strokeWidth="2" />
        <circle cx={x(end)} cy={y(last)} r="3.5" fill="currentColor" />
        <text x={PAD.left} y={PAD.top - 2} className="axis">{formatEur(max)}</text>
        <text x={PAD.left} y={H - PAD.bottom - 3} className="axis">{formatEur(min)}</text>
        <text x={PAD.left} y={H - 6} className="axis">{dateFormat.format(new Date(start))}</text>
        <text x={W - PAD.right} y={H - 6} className="axis" textAnchor="end">hoy</text>
        {hover != null && hoverT != null && hoverV != null && (
          <g>
            <line x1={hover} x2={hover} y1={PAD.top} y2={H - PAD.bottom} className="cursor" />
            <circle cx={hover} cy={y(hoverV)} r="3.5" fill="currentColor" />
            <text x={hover > W / 2 ? hover - 6 : hover + 6} y={PAD.top + 12} className="tip"
              textAnchor={hover > W / 2 ? 'end' : 'start'}>
              {dateFormat.format(new Date(hoverT))}: {formatEur(hoverV)}
            </text>
          </g>
        )}
      </svg>
    </section>
  )
}
