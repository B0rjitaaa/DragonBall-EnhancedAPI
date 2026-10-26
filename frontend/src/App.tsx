import { useCallback, useEffect, useMemo, useState } from 'react'
import CardGrid from './components/CardGrid'
import CardModal from './components/CardModal'
import FacetPanel from './components/FacetPanel'
import CollectionList from './components/CollectionList'
import Pagination from './components/Pagination'
import DeckView from './components/DeckView'
import OwnedPanel, { type Spot } from './components/OwnedPanel'
import QueryBuilder from './components/QueryBuilder'
import { api, ApiError, COLLECTION_BACKUP_URL, type Scope } from './lib/api'
import {
  buildQuery, countActive, newGroup, normalizeKeyword, readUrlState, writeUrlState,
} from './lib/query'
import { valueLabel } from './lib/labels'
import { SkillIndex } from './lib/skills'
import type { Facet, FacetState, FieldDef, Group, Location, OwnedSummary, SearchResponse } from './lib/types'

const PAGE_SIZE = 48

// Escáner de cartas (DragonBall-CameraCardChecker), en el mismo servidor.

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
 * El buscador. Con scope="collection" (página /collection, "Mi colección") se
 * comporta igual (filtros, modo avanzado, orden, páginas) pero solo sobre las
 * cartas escaneadas con el escáner, y muestra las copias de cada una.
 */
export default function App({ scope = 'all' }: { scope?: Scope }) {
  const inCollection = scope === 'collection'
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
  const [adjusting, setAdjusting] = useState<Set<number>>(() => new Set())
  // Mi colección: ubicaciones, la filtrada (null = todas) y el gestor.
  const [location, setLocation] = useState<number | null>(inCollection ? initial.location ?? null : null)
  // Ubicación pedida en la ruta (/collection/deck/<uid>): hasta conocer su id no se busca nada.
  const [pendingUid, setPendingUid] = useState<string | null>(inCollection ? initial.locationUid ?? null : null)
  const [locations, setLocations] = useState<Location[]>([])
  const [view, setView] = useState<'grid' | 'list' | 'deck'>(inCollection ? initial.view ?? 'grid' : 'grid')
  // Mi colección: por defecto solo cuentan las copias auténticas; con esto, también las falsas.
  // Dentro de una ubicación, «Mi orden»: el orden en que el usuario ha colocado sus cartas.
  const orderings: [string, string][] = inCollection
    ? [...(location != null ? [['position', 'Mi orden'] as [string, string]] : []), ...ORDERINGS, ['-quantity', 'Más copias']]
    : ORDERINGS
  const [showFakes, setShowFakes] = useState<boolean>(inCollection ? initial.showFakes ?? false : false)
  const [notice, setNotice] = useState<string | null>(null)
  // Se incrementa cuando algo fuera de la cuadrícula mueve copias (p. ej. hacer principal una versión del mazo).
  const [reloadTick, setReloadTick] = useState(0)

  const reloadLocations = useCallback(() => {
    if (!inCollection) return
    api
      .locations()
      .then(setLocations)
      .catch(() => setPendingUid(null)) // sin lista de ubicaciones, el resto sigue funcionando
  }, [inCollection])
  useEffect(reloadLocations, [reloadLocations])
  useEffect(() => {
    if (!pendingUid || !locations.length) return
    const found = locations.find((l) => l.uid === pendingUid)
    if (found) setLocation(found.id)
    else setNotice('Esa ubicación ya no existe: se muestra toda tu colección.')
    setPendingUid(null)
  }, [pendingUid, locations])
  // La ubicación filtrada ya no existe (se borró): se quita el filtro.
  useEffect(() => {
    if (location != null && locations.length && !locations.some((l) => l.id === location)) setLocation(null)
  }, [locations, location])
  // «Mi orden» solo existe dentro de una ubicación.
  useEffect(() => {
    if (location == null && !pendingUid && ordering === 'position') setOrdering('number')
  }, [location, ordering, pendingUid])
  // Dentro de un mazo, la vista «Mazo» (líder, estadísticas y reglas); fuera de un mazo no existe.
  const currentLocation = locations.find((l) => l.id === location)
  const isDeck = inCollection && currentLocation?.kind === 'deck'
  const [lastDeck, setLastDeck] = useState<number | null>(null)
  useEffect(() => {
    // Hasta saber qué ubicación pide la ruta no se sabe si es un mazo: no se cambia de vista.
    if (!locations.length || pendingUid) return
    if (isDeck && location !== lastDeck) {
      setLastDeck(location)
      if (view === 'grid') setView('deck')
    } else if (!isDeck && view === 'deck') {
      setView('grid')
    }
  }, [isDeck, location, lastDeck, view, locations.length, pendingUid])

  // Campos filtrables y keyword skills: no cambian, se piden una vez y sin esperar a nada
  // (la búsqueda solo necesita los campos; antes esperaba también a los recuentos).
  useEffect(() => {
    api
      .fields()
      .then(setFields)
      .catch((e: Error) => setBootError(e.message))
    api
      .keywordSkills()
      .then((d) => setSkills(new SkillIndex(d)))
      .catch(() => undefined) // sin tooltips si falla, el buscador sigue funcionando
  }, [])
  // Recuentos de los filtros (dependen del ámbito, la ubicación y las falsas).
  useEffect(() => {
    if (pendingUid) return
    api
      .facets(scope, location, showFakes)
      .then((fc) => setGlobalFacets(fc.facets))
      .catch((e: Error) => setBootError(e.message))
  }, [scope, location, showFakes, pendingUid])

  const query = useMemo(
    () => (fields.length ? buildQuery(facets, advanced, advancedOn, fields) : null),
    [facets, advanced, advancedOn, fields],
  )
  // Para cada campo con selección, sus recuentos se calculan SIN su propio filtro
  // (así en "Color: Red" siguen apareciendo cuántas cartas hay de Blue, Green…)
  const facetRequests = useMemo(() => {
    if (!fields.length) return []
    const reqs: { q: string; query: unknown; only?: string[]; scope: Scope; location: number | null; include_fakes: boolean }[] = [
      { q: q.trim(), query, scope, location, include_fakes: showFakes },
    ]
    for (const key of Object.keys(facets)) {
      const { [key]: _omit, ...rest } = facets
      void _omit
      reqs.push({ q: q.trim(), query: buildQuery(rest, advanced, advancedOn, fields), only: [key], scope, location, include_fakes: showFakes })
    }
    return reqs
  }, [q, query, facets, advanced, advancedOn, fields, scope, location, showFakes])
  const filterKey = useDebounced(JSON.stringify(facetRequests))
  // Solo se espera a que termine de escribir: el resto (ubicación, orden, página, filtros)
  // llega completo y busca al momento. Con todo retrasado, al abrir un mazo por su enlace
  // salía primero una búsqueda en toda la colección (aún sin la ubicación) que se tiraba.
  const typedQ = useDebounced(q.trim(), 150)
  const searchKey = JSON.stringify({
    q: typedQ, query, ordering, scope, location, include_fakes: showFakes,
    // Un mazo cabe entero en una página.
    page: view === 'deck' ? 1 : page,
    page_size: view === 'deck' ? 200 : PAGE_SIZE,
  })

  // Resultados
  useEffect(() => {
    if (!fields.length || pendingUid) return
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
  }, [searchKey, fields.length, pendingUid, reloadTick])

  // Recuentos de facetas dentro de la búsqueda actual
  useEffect(() => {
    if (!fields.length) return
    const reqs = JSON.parse(filterKey) as { q: string; query: unknown; only?: string[]; scope: Scope; location: number | null; include_fakes: boolean }[]
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

  const urlLocation = locations.find((l) => l.id === location) ?? null
  useEffect(() => {
    // Con una ubicación aún sin cargar no se toca la URL (se perdería su uid).
    if (pendingUid || (location != null && !urlLocation)) return
    writeUrlState({ q, facets, advanced, advancedOn, ordering, page, location, view, showFakes }, urlLocation)
  }, [q, facets, advanced, advancedOn, ordering, page, location, view, showFakes, pendingUid, urlLocation])

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
    setLocation(null)
    setShowFakes(false)
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

  // Mi colección: refleja en la página el resultado de una operación sobre una
  // carta. Con filtro de ubicación, sus copias son las de esa ubicación; si
  // llegan a 0, la carta sale de la lista sin preguntar.
  const applySummary = useCallback(
    (id: number, r: OwnedSummary) => {
      // Copias que cuentan con los filtros puestos (ubicación y/o solo falsas).
      const shown = r.locations
        .filter((l) => (location == null || l.id === location) && (showFakes || !l.fake))
        .reduce((n, l) => n + l.quantity, 0)
      setData((prev) => {
        if (!prev) return prev
        const before = prev.results.find((c) => c.id === id)?.quantity ?? 0
        const removed = shown === 0
        return {
          ...prev,
          count: removed ? prev.count - 1 : prev.count,
          total_copies: (prev.total_copies ?? 0) + (shown - before),
          results: removed
            ? prev.results.filter((c) => c.id !== id)
            : prev.results.map((c) =>
                c.id === id ? { ...c, quantity: shown, total_quantity: r.quantity, fakes: r.fakes, locations: r.locations } : c,
              ),
        }
      })
      if (shown === 0 && openId === id) setOpenId(null)
      reloadLocations() // los totales por ubicación del selector
    },
    [location, showFakes, openId, reloadLocations],
  )

  const runOnCard = useCallback(
    async (id: number, action: () => Promise<OwnedSummary>) => {
      if (adjusting.has(id)) return
      setAdjusting((s) => new Set(s).add(id))
      try {
        applySummary(id, await action())
        setError(null)
        setNotice(null)
      } catch (e) {
        if (e instanceof ApiError && e.status === 409) {
          // Copias repartidas en varias ubicaciones: se abre la ficha para elegir de cuál.
          setOpenId(id)
          setNotice('Esta carta está en varias ubicaciones: quita la copia desde la que quieras.')
        } else {
          setError(e instanceof Error ? e.message : String(e))
        }
      } finally {
        setAdjusting((s) => {
          const next = new Set(s)
          next.delete(id)
          return next
        })
      }
    },
    [adjusting, applySummary],
  )

  // − / + de la cuadrícula: con filtro de ubicación actúan sobre esa ubicación;
  // sin él, + suma a "Sin ubicar" y − quita de "Sin ubicar" (o pregunta).
  const adjust = useCallback(
    (id: number, delta: number, where?: number, fake?: boolean) =>
      runOnCard(id, () => api.adjustCollection(id, delta, where ?? location, fake ?? (showFakes ? undefined : false))),
    [runOnCard, location, showFakes],
  )
  const moveCopies = useCallback(
    (id: number, source: Spot, target: Spot, qty: number, noteLine?: string) =>
      runOnCard(id, () => api.moveCopies(id, source.location, target.location, qty, source.fake, target.fake, noteLine)),
    [runOnCard],
  )
  // Arrastrar para reordenar: solo dentro de una ubicación, en «Mi orden» y en cuadrícula.
  const canReorder = inCollection && location != null && ordering === 'position' && (view === 'grid' || view === 'deck')
  const reorder = useCallback(
    (ids: number[]) => {
      if (location == null) return
      setData((prev) => {
        if (!prev) return prev
        const byId = new Map(prev.results.map((c) => [c.id, c]))
        return { ...prev, results: ids.map((id) => byId.get(id)!).filter(Boolean) }
      })
      api.reorderCollection(location, ids).catch((e: Error) => setError(`No se pudo guardar el orden: ${e.message}`))
    },
    [location],
  )

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
              <span className="location-filter">
                <select
                  className="input"
                  value={location ?? ''}
                  onChange={(e) => {
                    const next = e.target.value ? Number(e.target.value) : null
                    setLocation(next)
                    if (next != null && ordering === 'number') setOrdering('position')
                    setPage(1)
                  }}
                  aria-label="Ubicación"
                >
                  <option value="">Todas las ubicaciones</option>
                  {locations.map((l) => (
                    <option key={l.id} value={l.id}>
                      {l.name} ({l.copies})
                    </option>
                  ))}
                </select>
                <label className="fake-filter" title="Contar y mostrar también las copias falsas">
                  <input
                    id="show-fakes"
                    type="checkbox"
                    checked={showFakes}
                    onChange={(e) => {
                      setShowFakes(e.target.checked)
                      setPage(1)
                    }}
                  />
                  Mostrar falsas
                </label>
                <a className="btn ghost" href="/locations">
                  Ubicaciones…
                </a>
                <span className="view-toggle" role="group" aria-label="Vista">
                  {isDeck && (
                    <button className={view === 'deck' ? 'on' : ''} onClick={() => setView('deck')} aria-pressed={view === 'deck'}>
                      Mazo
                    </button>
                  )}
                  <button className={view === 'grid' ? 'on' : ''} onClick={() => setView('grid')} aria-pressed={view === 'grid'}>
                    Cuadrícula
                  </button>
                  <button className={view === 'list' ? 'on' : ''} onClick={() => setView('list')} aria-pressed={view === 'list'}>
                    Lista
                  </button>
                </span>
              </span>
            )}
            {inCollection && (
              <a className="btn backup-link" href={COLLECTION_BACKUP_URL} download title="Descarga un JSON con tus ubicaciones y todas tus cartas, con sus copias en cada ubicación">
                Descargar copia
              </a>
            )}
            {inCollection && (
              <a className="btn primary scan-link" href="/scan">
                Escanear cartas
              </a>
            )}
          </div>

          {inCollection && view === 'deck' && currentLocation ? (
            <DeckView
              key={currentLocation.id}
              deck={currentLocation}
              onCollectionChanged={() => {
                setReloadTick((t) => t + 1)
                reloadLocations()
              }}
              cards={data?.results ?? []}
              loading={loading}
              onOpen={setOpenId}
              onReorder={canReorder ? reorder : undefined}
            />
          ) : inCollection && view === 'list' ? (
            <CollectionList
              cards={data?.results ?? []}
              locations={locations}
              filterLocation={location}
              showFakes={showFakes}
              loading={loading}
              busy={adjusting}
              onOpen={setOpenId}
              onMove={moveCopies}
            />
          ) : (
            <>
            {canReorder && (data?.results.length ?? 0) > 1 && (
              <p className="reorder-hint">Arrastra las cartas para ordenarlas (en el móvil, mantén pulsada una carta). El orden se guarda.</p>
            )}
            <CardGrid
              cards={data?.results ?? []}
              loading={loading}
              skills={skills}
              onOpen={setOpenId}
              quantities={quantities}
              onAdjust={inCollection ? adjust : undefined}
              adjusting={adjusting}
              showFakes={showFakes}
              onReorder={canReorder ? reorder : undefined}
              emptyText={
                inCollection && activeCount === 0
                  ? 'Tu colección está vacía: escanea cartas con el escáner y aparecerán aquí.'
                  : undefined
              }
            />
            </>
          )}

          {data && data.pages > 1 && view !== 'deck' && (
            <Pagination page={data.page} pages={data.pages} onPage={setPage} />
          )}
        </main>
      </div>

      {openId !== null && (
        <CardModal
          key={openId}
          id={openId}
          skills={skills}
          onClose={() => {
            setOpenId(null)
            setNotice(null)
          }}
          onFilter={addFilter}
        >
          {openOwned && (
            <OwnedPanel
              card={openOwned}
              locations={locations}
              busy={adjusting.has(openOwned.id)}
              notice={notice}
              onAdjust={(spot, delta) => void adjust(openOwned.id, delta, spot.location, delta < 0 ? spot.fake : undefined)}
              onMove={(source, target, qty, noteLine) => void moveCopies(openOwned.id, source, target, qty, noteLine)}
              onNote={(spot, notes) => void runOnCard(openOwned.id, () => api.setNote(openOwned.id, spot.location, notes, spot.fake))}
            />
          )}
        </CardModal>
      )}
    </div>
  )
}
