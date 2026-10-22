import { useState } from 'react'
import { api } from '../lib/api'
import type { Location, LocationKind } from '../lib/types'
import { KIND_LABELS } from './OwnedPanel'

const KINDS = Object.entries(KIND_LABELS) as [LocationKind, string][]

interface Props {
  locations: Location[]
  onChanged: () => void
  onClose: () => void
}

/** Crear, renombrar y borrar ubicaciones (al borrar, sus copias vuelven a "Sin ubicar"). */
export default function LocationsManager({ locations, onChanged, onClose }: Props) {
  const [name, setName] = useState('')
  const [kind, setKind] = useState<LocationKind>('deck')
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  const run = async (action: () => Promise<unknown>) => {
    setBusy(true)
    try {
      await action()
      setError(null)
      onChanged()
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e))
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal locations-modal" onClick={(e) => e.stopPropagation()} role="dialog" aria-label="Ubicaciones">
        <button className="icon-btn close" onClick={onClose} aria-label="Cerrar">
          ✕
        </button>
        <h2>Ubicaciones</h2>
        <p className="muted small">
          Dónde guardas las copias: mazos, archivadores, cajas… Lo escaneado entra en «Sin ubicar» salvo que elijas otra
          ubicación al empezar el modo ráfaga.
        </p>
        {error && <p className="error">{error}</p>}
        <ul className="locations-list">
          {locations.map((loc) => (
            <li key={loc.id}>
              {loc.is_default ? (
                <span className="loc-name">{loc.name}</span>
              ) : (
                <input
                  className="input loc-name"
                  defaultValue={loc.name}
                  maxLength={80}
                  aria-label="Nombre"
                  onBlur={(e) => {
                    const value = e.target.value.trim()
                    if (value && value !== loc.name) void run(() => api.updateLocation(loc.id, { name: value }))
                    else e.target.value = loc.name
                  }}
                  onKeyDown={(e) => e.key === 'Enter' && e.currentTarget.blur()}
                />
              )}
              {loc.is_default ? (
                <span />
              ) : (
                <select
                  className="input"
                  value={loc.kind}
                  aria-label="Tipo"
                  onChange={(e) => void run(() => api.updateLocation(loc.id, { kind: e.target.value as LocationKind }))}
                >
                  {KINDS.map(([v, l]) => (
                    <option key={v} value={v}>
                      {l}
                    </option>
                  ))}
                </select>
              )}
              <span className="muted small loc-count">
                {loc.cards} cartas · {loc.copies} copias
              </span>
              {loc.is_default ? (
                <span />
              ) : (
                <button
                  className="btn ghost"
                  disabled={busy}
                  onClick={() => {
                    const msg = loc.copies
                      ? `¿Borrar «${loc.name}»? Sus ${loc.copies} copias pasarán a «Sin ubicar».`
                      : `¿Borrar «${loc.name}»?`
                    if (window.confirm(msg)) void run(() => api.deleteLocation(loc.id))
                  }}
                  aria-label={`Borrar ${loc.name}`}
                >
                  Borrar
                </button>
              )}
            </li>
          ))}
        </ul>
        <form
          className="locations-new"
          onSubmit={(e) => {
            e.preventDefault()
            const value = name.trim()
            if (!value) return
            void run(async () => {
              await api.createLocation(value, kind)
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
      </div>
    </div>
  )
}
