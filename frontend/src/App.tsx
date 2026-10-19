import { useCallback, useEffect, useMemo, useState } from 'react'
import CardGrid from './components/CardGrid'
import CardModal from './components/CardModal'
import FacetPanel from './components/FacetPanel'
import QueryBuilder from './components/QueryBuilder'
import { api, type Scope } from './lib/api'
import {
  buildQuery, countActive, newGroup, normalizeKeyword, readUrlState, writeUrlState,
} from './lib/query'
import { valueLabel } from './lib/labels'
import { SkillIndex } from './lib/skills'
import type { Facet, FacetState, FieldDef, Group, SearchResponse } from './lib/types'

const PAGE_SIZE = 48
const CONDITIONS: Record<string, string> = {
  mint: 'Mint', near_mint: 'Near Mint', excellent: 'Excellent', good: 'Good', played: 'Played', poor: 'Poor',
}

// Escáner de cartas (DragonBall-CameraCardChecker), en el mismo servidor.
const SCANNER_URL = `http://${window.location.hostname}/`

const ORDERINGS: [string, string][] = [
  ['number', 'Número de carta'],
  ['-newest', 'Más antiguas'],
  ['newest', 'Más recientes'],
  ['name', 'Nombre A-Z'],
  ['energy', 'Energía ↑'],
  ['-energy', 'Energía ↓'],
  ['power', 'Poder ↑'],
  ['-power', 'Poder ↓'],
]

function useDebounced<T>(value: T, ms = 300): T {
  const [v, setV] = useState(value)
  useEffect(() => {
    const t = setTimeout(() => setV(value), ms)
    return () => clearTimeout(t)
  }, [value, ms])
  return v
}

/**
 * El buscador. Con scope="collection" (página /coleccion, "Mi colección") se
 * comporta igual (filtros, modo avanzado, orden, páginas) pero solo sobre las
 * cartas escaneadas con el escáner, y muestra las copias de cada una.
 */
export default function App({ scope = 'all' }: { scope?: Scope }) {
  const inCollection = scope === 'collection'
  const orderings: [string, string][] = inCollection ? [...ORDERINGS, ['-quantity', 'Más copias']] : ORDERINGS
  const [initial] = useState(readUrlState)
  const [fields, setFields] = useState<FieldDef[]>([])
  const [globalFacets, setGlobalFacets] = useState<Record<string, Facet>>({})
  const [contextFacets, setContextFacets] = useState<Record<string, Facet> | null>(null)
  const [bootError, setBootError] = useState<string | null>(null)
  const [skills, setSkills] = useState<SkillIndex>(SkillIndex.empty)

  const [q, setQ] = useState(initial.q ?? '')
  const [facets, setFacets] = useState<FacetState>(initial.facets ?? {})
  const [advanced, setAdvanced] = useState<Group>(initial.advanced ?? newGroup())
  const [advancedOn, setAdvancedOn] = useState(initial.advancedOn ?? false)
  const [ordering, setOrdering] = useState(initial.ordering ?? 'number')
  const [page, setPage] = useState(initial.page ?? 1)

  const [data, setData] = useState<SearchResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [openId, setOpenId] = useState<number | null>(null)
  const [sidebarOpen, setSidebarOpen] = useState(false)

  useEffect(() => {
    Promise.all([api.fields(), api.facets(scope)])
      .then(([f, fc]) => {
        setFields(f)
        setGlobalFacets(fc.facets)
      })
      .catch((e: Error) => setBootError(e.message))
    api
      .keywordSkills()
      .then((d) => setSkills(new SkillIndex(d)))
      .catch(() => undefined) // sin tooltips si falla, el buscador sigue funcionando
  }, [scope])

  const query = useMemo(
    () => (fields.length ? buildQuery(facets, advanced, advancedOn, fields) : null),
    [facets, advanced, advancedOn, fields],
  )
  // Para cada campo con selección, sus recuentos se calculan SIN su propio filtro
  // (así en "Color: Red" siguen apareciendo cuántas cartas hay de Blue, Green…)
  const facetRequests = useMemo(() => {
    if (!fields.length) return []
    const reqs: { q: string; query: unknown; only?: string[]; scope: Scope }[] = [{ q: q.trim(), query, scope }]
    for (const key of Object.keys(facets)) {
      const { [key]: _omit, ...rest } = facets
      void _omit
      reqs.push({ q: q.trim(), query: buildQuery(rest, advanced, advancedOn, fields), only: [key], scope })
    }
    return reqs
  }, [q, query, facets, advanced, advancedOn, fields, scope])
  const filterKey = useDebounced(JSON.stringify(facetRequests))
  const searchKey = useDebounced(JSON.stringify({ q: q.trim(), query, ordering, page, page_size: PAGE_SIZE, scope }), 150)

  // Resultados
  useEffect(() => {
    if (!fields.length) return
    const ctrl = new AbortController()
    setLoading(true)
    api
      .search(JSON.parse(searchKey), ctrl.signal)
      .then((r) => {
        setData(r)
        setError(null)
      })
      .catch((e: Error) => e.name !== 'AbortError' && setError(e.message))
      .finally(() => !ctrl.signal.aborted && setLoading(false))
    return () => ctrl.abort()
  }, [searchKey, fields.length])

  // Recuentos de facetas dentro de la búsqueda actual
  useEffect(() => {
    if (!fields.length) return
    const reqs = JSON.parse(filterKey) as { q: string; query: unknown; only?: string[]; scope: Scope }[]
    if (!reqs.length || (!reqs[0].q && !reqs[0].query)) {
      setContextFacets(null)
      return
    }
    const ctrl = new AbortController()
    Promise.all(reqs.map((r) => api.facetsFor(r, ctrl.signal)))
      .then(([base, ...perField]) => setContextFacets(Object.assign({}, base.facets, ...perField.map((r) => r.facets))))
      .catch(() => undefined)
    return () => ctrl.abort()
  }, [filterKey, fields.length])

  useEffect(() => {
    writeUrlState({ q, facets, advanced, advancedOn, ordering, page })
  }, [q, facets, advanced, advancedOn, ordering, page])

  useEffect(() => {
    // En Chrome reciente scrollTo devuelve una Promise: no puede ser el valor de retorno del efecto
    window.scrollTo({ top: 0, behavior: 'smooth' })
  }, [page])

  // En móvil el panel de filtros tapa la cabecera: Escape también lo cierra y el fondo no scrollea
  useEffect(() => {
    if (!sidebarOpen) return
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') setSidebarOpen(false)
    }
    document.addEventListener('keydown', onKey)
    document.body.classList.add('no-scroll')
    return () => {
      document.removeEventListener('keydown', onKey)
      document.body.classList.remove('no-scroll')
    }
  }, [sidebarOpen])

  const changeFacets = (next: FacetState) => {
    setFacets(next)
    setPage(1)
  }

  const addFilter = useCallback((requested: string, raw: string) => {
    // Un corchete del texto ('[Over Realm 3]') filtra por su keyword skill oficial ('Over Realm X')
    const official = requested === 'keyword' ? skills.officialName(raw) : raw
    const field = requested === 'keyword' ? skills.fieldFor(official) : requested
    const value = field === 'keyword' ? normalizeKeyword(raw) : official
    setFacets((prev) => {
      const sel = prev[field] ?? { values: [], match: 'all' as const }
      if (sel.values.includes(value)) return prev
      return { ...prev, [field]: { ...sel, values: [...sel.values, value] } }
    })
    setPage(1)
    setOpenId(null)
  }, [skills])

  const clearAll = () => {
    setQ('')
    setFacets({})
    setAdvanced(newGroup())
    setPage(1)
  }

  // La bola de dragón vuelve al estado inicial: sin búsqueda, sin filtros y sin modo avanzado
  const goHome = () => {
    clearAll()
    setAdvancedOn(false)
    setOrdering('number')
    setOpenId(null)
    setSidebarOpen(false)
    window.scrollTo({ top: 0, behavior: 'smooth' })
  }

  const labels = useMemo(() => Object.fromEntries(fields.map((f) => [f.key, f.label])), [fields])
  // Mi colección: copias de cada carta de la página (insignia ×N y ficha).
  const quantities = useMemo(
    () => (inCollection ? Object.fromEntries((data?.results ?? []).map((c) => [c.id, c.quantity ?? 0])) : undefined),
    [data, inCollection],
  )
  const openOwned = inCollection ? data?.results.find((c) => c.id === openId) : undefined
  const activeCount = countActive(facets) + (advancedOn ? advanced.children.length : 0) + (q ? 1 : 0)

  if (bootError) {
    return (
      <div className="boot-error">
        <h1>{inCollection ? 'No se puede cargar Mi colección' : 'No se puede conectar con la API'}</h1>
        <p>{bootError}</p>
        <p className="muted">¿Está levantado el backend? Prueba <code>docker compose ps</code>.</p>
      </div>
    )
  }

  return (
    <div className="app">
      <header className="topbar">
        <button
          className="icon-btn menu"
          onClick={() => setSidebarOpen(!sidebarOpen)}
          aria-label="Filtros"
          aria-expanded={sidebarOpen}
        >
          ☰
        </button>
        <button className="brand" onClick={goHome} title="Volver al inicio y limpiar los filtros">
          <span className="ball" aria-hidden>★</span>
          <span className="brand-text">
            <strong>{inCollection ? 'Mi colección' : 'DragonBall EnhancedAPI'}</strong>
            <small>{inCollection ? 'Cartas escaneadas con el escáner de cartas' : 'Buscador de cartas · Dragon Ball Super Card Game'}</small>
          </span>
        </button>
        <input
          className="input search"
          type="search"
          placeholder={inCollection ? 'Buscar en mi colección por nombre, número o texto…' : 'Buscar por nombre, número o texto…'}
          value={q}
          onChange={(e) => {
            setQ(e.target.value)
            setPage(1)
          }}
        />
        <select className="input" value={ordering} onChange={(e) => setOrdering(e.target.value)} aria-label="Ordenar">
          {orderings.map(([v, l]) => (
            <option key={v} value={v}>
              {l}
            </option>
          ))}
        </select>
        <button
          className={`btn ${advancedOn ? 'primary' : 'ghost'}`}
          onClick={() => {
            setAdvancedOn(!advancedOn)
            setPage(1)
          }}
        >
          Modo avanzado {advancedOn ? 'ON' : 'OFF'}
        </button>
      </header>

      <div className="layout">
        {sidebarOpen && <div className="backdrop" onClick={() => setSidebarOpen(false)} aria-hidden />}
        <aside className={`sidebar ${sidebarOpen ? 'open' : ''}`}>
          <div className="sidebar-head">
            <strong>Filtros</strong>
            <span className="sidebar-actions">
              {activeCount > 0 && (
                <button className="link small" onClick={clearAll}>
                  Limpiar todo
                </button>
              )}
              <button className="icon-btn close-filters" onClick={() => setSidebarOpen(false)} aria-label="Cerrar filtros">
                ✕
              </button>
            </span>
          </div>
          {fields.length > 0 && (
            <FacetPanel
              fields={fields}
              global={globalFacets}
              context={contextFacets}
              state={facets}
              onChange={changeFacets}
              skills={skills}
            />
          )}
          <div className="sidebar-foot">
            <button className="btn primary" onClick={() => setSidebarOpen(false)}>
              Ver {data ? data.count.toLocaleString('es-ES') : ''} cartas
            </button>
          </div>
        </aside>

        <main className="content">
          {advancedOn && fields.length > 0 && (
            <section className="panel">
              <div className="panel-head">
                <h2>Búsqueda avanzada</h2>
                <span className="muted small">Se combina (Y) con los filtros del panel lateral</span>
              </div>
              <QueryBuilder
                tree={advanced}
                fields={fields}
                facets={globalFacets}
                onChange={(t) => {
                  setAdvanced(t)
                  setPage(1)
                }}
              />
            </section>
          )}

          {Object.keys(facets).length > 0 && (
            <div className="active-filters">
              {Object.entries(facets).flatMap(([key, sel]) => [
                ...sel.values.map((v) => (
                  <span key={`${key}-${v}`} className="tag">
                    <small>{labels[key]}:</small> {valueLabel(key, v)}
                    <button
                      onClick={() => changeFacets({ ...facets, [key]: { ...sel, values: sel.values.filter((x) => x !== v) } })}
                      aria-label="Quitar"
                    >
                      ×
                    </button>
                  </span>
                )),
                ...((sel.min ?? '') !== '' || (sel.max ?? '') !== ''
                  ? [
                      <span key={`${key}-range`} className="tag">
                        <small>{labels[key]}:</small> {sel.min === '' || sel.min == null ? '…' : sel.min} – {sel.max === '' || sel.max == null ? '…' : sel.max}
                        <button onClick={() => changeFacets({ ...facets, [key]: { ...sel, min: '', max: '' } })} aria-label="Quitar">
                          ×
                        </button>
                      </span>,
                    ]
                  : []),
              ])}
            </div>
          )}

          {inCollection && data?.missing && data.missing.length > 0 && (
            <div className="legal-banner limited">
              {data.missing.length} carta(s) escaneada(s) aún no están en este catálogo (¿set nuevo? aparecerán tras el
              próximo sync): {data.missing.join(', ')}
            </div>
          )}

          <div className="results-head">
            <span>
              {data ? (
                <>
                  <strong>{data.count.toLocaleString('es-ES')}</strong> cartas
                  {inCollection && data.total_copies != null && (
                    <>
                      {' '}· <strong>{data.total_copies.toLocaleString('es-ES')}</strong> copias
                    </>
                  )}
                </>
              ) : (
                'Cargando…'
              )}
            </span>
            {error && <span className="error">{error}</span>}
            {inCollection && (
              <a className="btn primary scan-link" href={SCANNER_URL}>
                Escanear cartas ↗
              </a>
            )}
          </div>

          <CardGrid
            cards={data?.results ?? []}
            loading={loading}
            skills={skills}
            onOpen={setOpenId}
            quantities={quantities}
            emptyText={
              inCollection && activeCount === 0
                ? 'Tu colección está vacía: escanea cartas con el escáner y aparecerán aquí.'
                : undefined
            }
          />

          {data && data.pages > 1 && (
            <nav className="pagination">
              <button className="btn ghost" disabled={page <= 1} onClick={() => setPage(page - 1)}>
                ← Anterior
              </button>
              <span>
                Página {data.page} de {data.pages}
              </span>
              <button className="btn ghost" disabled={page >= data.pages} onClick={() => setPage(page + 1)}>
                Siguiente →
              </button>
            </nav>
          )}
        </main>
      </div>

      {openId !== null && <CardModal key={openId} id={openId} skills={skills} onClose={() => setOpenId(null)} onFilter={addFilter} />}
      {openOwned && (
        <div className="owned-pill" role="status">
          En tu colección: <strong>×{openOwned.quantity}</strong>
          {' · '}
          {Object.entries(openOwned.conditions ?? {})
            .map(([cond, n]) => `${n} ${CONDITIONS[cond] ?? cond}`)
            .join(', ')}
        </div>
      )}
    </div>
  )
}
