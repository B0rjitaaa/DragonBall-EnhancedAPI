// Botones de las wants (cartas que quiero comprar): el corazón de cada carta en el buscador y el panel de la
// ficha, debajo de «Add to My collection».
import { useState } from 'react'
import { setWant, useWants } from '../lib/wants'

/** En la esquina de la carta: ♡ la añade a mis wants (1 copia); ♥ la quita. */
export function WantToggle({ id, name }: { id: number; name: string }) {
  const wants = useWants()
  const n = wants?.[id] ?? 0
  return (
    <button
      type="button"
      className={`want-toggle ${n ? 'on' : ''}`}
      disabled={wants == null}
      aria-pressed={n > 0}
      aria-label={n ? `Remove ${name} from my wants` : `Add ${name} to my wants`}
      title={n ? `In your wants (×${n}) · click to remove` : 'Add to my wants'}
      onClick={() => void setWant(id, n ? 0 : 1).catch((e: Error) => window.alert(e.message))}
    >
      <span aria-hidden>{n ? '♥' : '♡'}</span>
      {n > 1 && <small>{n}</small>}
    </button>
  )
}

/** En la ficha: si está en mis wants y cuántas copias quiero (− / +), o el botón para añadirla. */
export function WantPanel({ id }: { id: number }) {
  const wants = useWants()
  const [error, setError] = useState<string | null>(null)
  if (wants == null) return null
  const n = wants[id] ?? 0
  const change = (q: number) => {
    setError(null)
    void setWant(id, Math.max(0, Math.min(99, q))).catch((e: Error) => setError(e.message))
  }
  return (
    <section className={`want-panel ${n ? 'on' : ''}`} aria-label="My wants">
      {n === 0 ? (
        <button type="button" className="btn want-add" onClick={() => change(1)}>
          ♡ Add to my wants
        </button>
      ) : (
        <div className="want-row">
          <span>
            ♥ In <a href="/wants">my wants</a>
          </span>
          <span className="owned-qty">
            <button className="qty-btn" onClick={() => change(n - 1)} aria-label="Want one copy less">
              −
            </button>
            <strong title="Copies you want">×{n}</strong>
            <button className="qty-btn" onClick={() => change(n + 1)} disabled={n >= 99} aria-label="Want one more copy">
              +
            </button>
          </span>
          <button type="button" className="link small" onClick={() => change(0)}>
            Remove
          </button>
        </div>
      )}
      {error && <p className="error small">{error}</p>}
    </section>
  )
}
