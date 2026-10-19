import { useCallback, useEffect, useMemo, useState } from 'react'
import CardGrid from './components/CardGrid'
import CardModal from './components/CardModal'
import { api } from './lib/api'
import { normalizeKeyword, searchUrlWithFilter } from './lib/query'
import { SkillIndex } from './lib/skills'
import type { CollectionCard, MyCollectionResponse } from './lib/types'

// "Mi colección": las cartas escaneadas con DragonBall-CameraCardChecker, con
// la ficha de este catálogo. Solo lectura: las copias se gestionan escaneando.

const ORDERINGS: [string, string, (a: CollectionCard, b: CollectionCard) => number][] = [
  ['number', 'Número de carta', () => 0], // el backend ya las devuelve en orden de catálogo
  ['name', 'Nombre A-Z', (a, b) => a.name.localeCompare(b.name)],
  ['-quantity', 'Más copias', (a, b) => b.quantity - a.quantity],
  ['-power', 'Poder ↓', (a, b) => (b.power ?? -1) - (a.power ?? -1)],
]

const CONDITIONS: Record<string, string> = {
  mint: 'Mint', near_mint: 'Near Mint', excellent: 'Excellent', good: 'Good', played: 'Played', poor: 'Poor',
}

const SCANNER_URL = `http://${window.location.hostname}/`

export default function MyCollection() {
  const [data, setData] = useState<MyCollectionResponse | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const [q, setQ] = useState('')
  const [ordering, setOrdering] = useState('number')
  const [openId, setOpenId] = useState<number | null>(null)
  const [skills, setSkills] = useState<SkillIndex>(SkillIndex.empty)

  const load = useCallback(() => {
    setLoading(true)
    api
      .myCollection()
      .then((d) => {
        setData(d)
        setError(null)
      })
      .catch((e: Error) => setError(e.message))
      .finally(() => setLoading(false))
  }, [])

  useEffect(() => {
    load()
    api.keywordSkills().then((d) => setSkills(new SkillIndex(d))).catch(() => undefined)
  }, [load])

  const cards = useMemo(() => {
    const term = q.trim().toLowerCase()
    const list = (data?.results ?? []).filter(
      (c) => !term || c.name.toLowerCase().includes(term) || c.card_number.toLowerCase().includes(term),
    )
    const sorter = ORDERINGS.find(([key]) => key === ordering)?.[2]
    return sorter ? [...list].sort(sorter) : list
  }, [data, q, ordering])

  const quantities = useMemo(() => Object.fromEntries((data?.results ?? []).map((c) => [c.id, c.quantity])), [data])
  const open = data?.results.find((c) => c.id === openId)

  // Un filtro pulsado en la ficha (keyword, rasgo…) abre el buscador con ese filtro.
  const goFilter = (requested: string, raw: string) => {
    const official = requested === 'keyword' ? skills.officialName(raw) : raw
    const field = requested === 'keyword' ? skills.fieldFor(official) : requested
    const value = field === 'keyword' ? normalizeKeyword(raw) : official
    window.location.href = searchUrlWithFilter(field, value)
  }

  return (
    <div className="app">
      <header className="topbar">
        <a className="brand" href="/" title="Ir al buscador">
          <span className="ball" aria-hidden>★</span>
          <span className="brand-text">
            <strong>Mi colección</strong>
            <small>Cartas escaneadas con el escáner de cartas</small>
          </span>
        </a>
        <input
          className="input search"
          type="search"
          placeholder="Buscar en mi colección por nombre o número…"
          value={q}
          onChange={(e) => setQ(e.target.value)}
        />
        <select className="input" value={ordering} onChange={(e) => setOrdering(e.target.value)} aria-label="Ordenar">
          {ORDERINGS.map(([v, l]) => (
            <option key={v} value={v}>
              {l}
            </option>
          ))}
        </select>
        <button className="btn ghost" onClick={load} disabled={loading}>
          Actualizar
        </button>
      </header>

      <main className="content collection-page">
        <div className="results-head">
          <span>
            {data ? (
              <>
                <strong>{data.total_cards.toLocaleString('es-ES')}</strong> cartas distintas ·{' '}
                <strong>{data.total_copies.toLocaleString('es-ES')}</strong> copias
                {q && <> · {cards.length} coinciden</>}
              </>
            ) : loading ? (
              'Cargando…'
            ) : null}
          </span>
          <a className="btn primary" href={SCANNER_URL}>
            Escanear cartas ↗
          </a>
        </div>
        {error && (
          <div className="legal-banner banned">
            No se pudo leer la colección: {error}
          </div>
        )}
        {data && data.missing.length > 0 && (
          <div className="legal-banner limited">
            {data.missing.length} carta(s) escaneada(s) aún no están en este catálogo (¿set nuevo? se verán tras el
            próximo sync): {data.missing.join(', ')}
          </div>
        )}
        <CardGrid
          cards={cards}
          loading={loading}
          skills={skills}
          onOpen={setOpenId}
          quantities={quantities}
          emptyText={
            data && data.total_cards === 0
              ? 'Tu colección está vacía: escanea cartas con el escáner y aparecerán aquí.'
              : 'Ninguna carta de tu colección coincide con la búsqueda.'
          }
        />
      </main>

      {openId !== null && (
        <>
          <CardModal key={openId} id={openId} skills={skills} onClose={() => setOpenId(null)} onFilter={goFilter} />
          {open && (
            <div className="owned-pill" role="status">
              En tu colección: <strong>×{open.quantity}</strong>
              {' · '}
              {Object.entries(open.conditions)
                .map(([cond, n]) => `${n} ${CONDITIONS[cond] ?? cond}`)
                .join(', ')}
            </div>
          )}
        </>
      )}
    </div>
  )
}
