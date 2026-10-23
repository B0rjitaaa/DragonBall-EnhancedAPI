import { useCallback, useEffect, useState } from 'react'
import { KIND_LABELS } from './components/OwnedPanel'
import { api } from './lib/api'
import type { Location, LocationKind } from './lib/types'

const KINDS = Object.entries(KIND_LABELS) as [LocationKind, string][]
const KIND_SECTIONS: [LocationKind, string][] = [
  ['deck', 'Mazos'],
  ['binder', 'Archivadores'],
  ['storage', 'Almacén'],
  ['other', 'Otras'],
]

/** Enlace a Mi colección filtrada por una ubicación (el estado de la búsqueda va en el #). */
export function collectionUrl(location: number): string {
  return `/coleccion#${encodeURIComponent(JSON.stringify({ location }))}`
}

/** Pantalla de ubicaciones de Mi colección: crear, editar, ordenar y borrar. */
export default function LocationsPage() {
  const [locations, setLocations] = useState<Location[] | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  const [name, setName] = useState('')
  const [kind, setKind] = useState<LocationKind>('deck')

  const reload = useCallback(() => {
    api
      .locations()
      .then((l) => {
        setLocations(l)
        setError(null)
      })
      .catch((e: Error) => setError(e.message))
  }, [])
  useEffect(reload, [reload])

  const run = async (action: () => Promise<unknown>) => {
    setBusy(true)
    try {
      await action()
      setError(null)
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e))
    } finally {
      setBusy(false)
      reload()
    }
  }

  if (!locations) {
    return <div className="locations-page">{error ? <p className="error">{error}</p> : <p className="muted">Cargando…</p>}</div>
  }

  const unplaced = locations.find((l) => l.is_default)
  const custom = locations.filter((l) => !l.is_default)
  // Reordenar dentro de su tipo: se reescriben las posiciones de todas.
  const move = (loc: Location, step: -1 | 1) => {
    const order = [...custom]
    const i = order.findIndex((l) => l.id === loc.id)
    const sameKind = order.filter((l) => l.kind === loc.kind)
    const k = sameKind.findIndex((l) => l.id === loc.id)
    const other = sameKind[k + step]
    if (!other) return
    const j = order.findIndex((l) => l.id === other.id)
    ;[order[i], order[j]] = [order[j], order[i]]
    void run(() =>
      Promise.all(
        order.map((l, pos) => (l.position === pos + 1 ? null : api.updateLocation(l.id, { position: pos + 1 }))),
      ),
    )
  }

  return (
    <div className="locations-page">
      <header className="locations-page-head">
        <div>
          <h1>Ubicaciones</h1>
          <p className="muted">
            Dónde guardas las copias: mazos, archivadores, cajas… Lo escaneado entra en «Sin ubicar» salvo que elijas otra
            ubicación al empezar el modo ráfaga. Para mover cartas, usa el modo{' '}
            <a href={`/coleccion#${encodeURIComponent(JSON.stringify({ view: 'list' }))}`}>Lista de Mi colección</a>.
          </p>
        </div>
        <form
          className="locations-new"
          onSubmit={(e) => {
            e.preventDefault()
            const value = name.trim()
            if (!value) return
            void run(async () => {
              await api.createLocation(value, kind, Math.max(0, ...locations.map((l) => l.position)) + 1)
              setName('')
            })
          }}
        >
          <input
            className="input"
            placeholder="Nueva ubicación (p. ej. Mazo Goku azul)"
            value={name}
            maxLength={80}
            onChange={(e) => setName(e.target.value)}
            aria-label="Nombre de la nueva ubicación"
          />
          <select className="input" value={kind} onChange={(e) => setKind(e.target.value as LocationKind)} aria-label="Tipo">
            {KINDS.map(([v, l]) => (
              <option key={v} value={v}>
                {l}
              </option>
            ))}
          </select>
          <button className="btn primary" disabled={busy || !name.trim()}>
            Crear
          </button>
        </form>
      </header>
      {error && <p className="error">{error}</p>}

      {unplaced && (
        <section className="loc-section">
          <div className="loc-grid">
            <LocationCard loc={unplaced} busy={busy} run={run} />
          </div>
        </section>
      )}
      {KIND_SECTIONS.map(([k, title]) => {
        const items = custom.filter((l) => l.kind === k)
        if (!items.length) return null
        return (
          <section key={k} className="loc-section">
            <h2>
              {title} <small className="muted">{items.length}</small>
            </h2>
            <div className="loc-grid">
              {items.map((loc, i) => (
                <LocationCard
                  key={loc.id}
                  loc={loc}
                  busy={busy}
                  run={run}
                  onUp={i > 0 ? () => move(loc, -1) : undefined}
                  onDown={i < items.length - 1 ? () => move(loc, 1) : undefined}
                />
              ))}
            </div>
          </section>
        )
      })}
      {!custom.length && (
        <p className="empty">Aún no tienes ubicaciones: crea la primera arriba (un mazo, un archivador, una caja…).</p>
      )}
    </div>
  )
}

function LocationCard({
  loc,
  busy,
  run,
  onUp,
  onDown,
}: {
  loc: Location
  busy: boolean
  run: (action: () => Promise<unknown>) => Promise<void>
  onUp?: () => void
  onDown?: () => void
}) {
  const save = (changes: Partial<Pick<Location, 'name' | 'kind' | 'notes'>>) => void run(() => api.updateLocation(loc.id, changes))

  return (
    <article className={`loc-card kind-${loc.kind}`}>
      {loc.leader && (
        <a className="loc-leader" href={collectionUrl(loc.id)} title={`${loc.leader.card_number} · ${loc.leader.name}`}>
          <img src={loc.leader.image} alt={`Líder: ${loc.leader.name}`} loading="lazy" referrerPolicy="no-referrer" />
          <span>{loc.leader.name}</span>
        </a>
      )}
      <div className="loc-card-head">
        {loc.is_default ? (
          <strong className="loc-title">{loc.name}</strong>
        ) : (
          <input
            className="input loc-title"
            defaultValue={loc.name}
            maxLength={80}
            aria-label="Nombre"
            onBlur={(e) => {
              const value = e.target.value.trim()
              if (value && value !== loc.name) save({ name: value })
              else e.target.value = loc.name
            }}
            onKeyDown={(e) => e.key === 'Enter' && e.currentTarget.blur()}
          />
        )}
        {(onUp || onDown) && (
          <span className="loc-order">
            <button className="icon-btn" disabled={busy || !onUp} onClick={onUp} aria-label="Subir">
              ↑
            </button>
            <button className="icon-btn" disabled={busy || !onDown} onClick={onDown} aria-label="Bajar">
              ↓
            </button>
          </span>
        )}
      </div>
      <p className="loc-stats">
        <strong>{loc.copies}</strong> copias · {loc.cards} cartas
        {loc.fakes > 0 && (
          <>
            {' · '}
            <a className="fake-link" href={`/coleccion#${encodeURIComponent(JSON.stringify({ location: loc.id, showFakes: true }))}`}>
              {loc.fakes === 1 ? '1 falsa' : `${loc.fakes} falsas`}
            </a>
          </>
        )}
      </p>
      {loc.is_default ? (
        <p className="muted small">Lo que aún no has guardado en ningún sitio. No se puede borrar.</p>
      ) : (
        <>
          <select
            className="input"
            value={loc.kind}
            aria-label="Tipo"
            onChange={(e) => save({ kind: e.target.value as LocationKind })}
          >
            {KINDS.map(([v, l]) => (
              <option key={v} value={v}>
                {l}
              </option>
            ))}
          </select>
          <textarea
            className="input loc-notes"
            defaultValue={loc.notes}
            placeholder="Notas (p. ej. caja azul del armario)"
            maxLength={500}
            rows={2}
            onBlur={(e) => e.target.value !== loc.notes && save({ notes: e.target.value })}
          />
        </>
      )}
      <div className="loc-actions">
        <a className="btn" href={collectionUrl(loc.id)}>
          Ver cartas
        </a>
        {!loc.is_default && (
          <button
            className="btn ghost"
            disabled={busy}
            onClick={() => {
              const msg = loc.copies
                ? `¿Borrar «${loc.name}»? Sus ${loc.copies} copias pasarán a «Sin ubicar».`
                : `¿Borrar «${loc.name}»?`
              if (window.confirm(msg)) void run(() => api.deleteLocation(loc.id))
            }}
          >
            Borrar
          </button>
        )}
      </div>
    </article>
  )
}
