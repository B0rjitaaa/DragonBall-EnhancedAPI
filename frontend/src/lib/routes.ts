/**
 * Rutas de la web (en inglés). Los enlaces antiguos en español (/coleccion/mazo/…,
 * ?orden=…) se reescriben a los nuevos al cargar, así siguen funcionando.
 */
export type Page = 'search' | 'collection' | 'locations' | 'scan'

const LEGACY_PATHS: [RegExp, string][] = [
  [/^\/coleccion\/mazo\//, '/collection/deck/'],
  [/^\/coleccion\/ubicacion\//, '/collection/location/'],
  [/^\/coleccion(?=\/|$)/, '/collection'],
  [/^\/ubicaciones(?=\/|$)/, '/locations'],
  [/^\/escaner(?=\/|$)/, '/scan'],
]
const LEGACY_PARAMS: Record<string, string> = {
  orden: 'sort',
  pagina: 'page',
  vista: 'view',
  falsas: 'fakes',
  filtros: 'filters',
  avanzado: 'advanced',
  avanzado_on: 'advanced_on',
}

/** Cambia en la barra de direcciones un enlace antiguo por su equivalente nuevo. */
export function upgradeLegacyUrl(): void {
  const { pathname, search, hash } = window.location
  let path = pathname
  for (const [pattern, replacement] of LEGACY_PATHS) path = path.replace(pattern, replacement)
  const params = new URLSearchParams(search)
  let renamed = false
  for (const [old, name] of Object.entries(LEGACY_PARAMS)) {
    const value = params.get(old)
    if (value == null) continue
    params.delete(old)
    params.set(name, value)
    renamed = true
  }
  if (path !== pathname || renamed) {
    const query = params.toString()
    window.history.replaceState(null, '', `${path}${query ? `?${query}` : ''}${hash}`)
  }
}

export function currentPage(): Page {
  const path = window.location.pathname.replace(/\/+$/, '')
  if (path === '/collection' || path.startsWith('/collection/')) return 'collection'
  if (path === '/locations') return 'locations'
  if (path === '/scan') return 'scan'
  return 'search'
}
