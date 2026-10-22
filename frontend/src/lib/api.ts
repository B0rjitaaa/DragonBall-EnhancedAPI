import type {
  CardDetail, FacetsResponse, FieldDef, KeywordSkillsResponse, Location, LocationKind, OwnedSummary, SearchResponse,
} from './types'

const BASE = import.meta.env.VITE_API_URL ?? '/api'

/** Descarga directa (enlace) de la copia de seguridad de Mi colección. */
export const COLLECTION_BACKUP_URL = `${BASE}/my-collection/backup/`

/** Error de la API con su estado HTTP y el cuerpo (p. ej. el 409 de quitar una copia repartida). */
export class ApiError extends Error {
  readonly status: number
  readonly body: unknown

  constructor(message: string, status: number, body: unknown) {
    super(message)
    this.status = status
    this.body = body
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    ...init,
    headers: { 'Content-Type': 'application/json', ...(init?.headers ?? {}) },
  })
  if (!res.ok) {
    let detail = `${res.status} ${res.statusText}`
    let body: unknown = null
    try {
      body = await res.json()
      detail =
        body && typeof body === 'object' && 'detail' in body
          ? String((body as { detail: unknown }).detail)
          : typeof body === 'object' ? Object.values(body as object).flat().join(' · ') : String(body)
    } catch {
      /* respuesta sin JSON */
    }
    throw new ApiError(detail, res.status, body)
  }
  return (res.status === 204 ? undefined : res.json()) as Promise<T>
}

const post = (body: unknown) => ({ method: 'POST', body: JSON.stringify(body) })

export interface SearchBody {
  q?: string
  query?: unknown
  ordering?: string
  page?: number
  page_size?: number
  /** 'collection': solo las cartas de Mi colección */
  scope?: Scope
  /** Con scope 'collection': solo las copias de esa ubicación */
  location?: number | null
}

export type Scope = 'all' | 'collection'

export const api = {
  fields: () => request<FieldDef[]>('/fields/'),
  facets: (scope: Scope = 'all', location: number | null = null) =>
    request<FacetsResponse>(
      scope === 'collection' ? `/facets/?scope=collection${location ? `&location=${location}` : ''}` : '/facets/',
    ),
  facetsFor: (body: SearchBody & { only?: string[] }, signal?: AbortSignal) =>
    request<FacetsResponse>('/facets/', { method: 'POST', body: JSON.stringify(body), signal }),
  search: (body: SearchBody, signal?: AbortSignal) =>
    request<SearchResponse>('/cards/search/', { method: 'POST', body: JSON.stringify(body), signal }),
  card: (id: number) => request<CardDetail>(`/cards/${id}/`),
  keywordSkills: () => request<KeywordSkillsResponse>('/keyword-skills/'),
  /** Mi colección: suma (delta > 0) o resta copias; sin `location`, + va a "Sin ubicar". */
  adjustCollection: (cardId: number, delta: number, location?: number | null) =>
    request<OwnedSummary>('/my-collection/adjust/', post({ card_id: cardId, delta, ...(location ? { location } : {}) })),
  moveCopies: (cardId: number, source: number, target: number, quantity: number) =>
    request<OwnedSummary>('/my-collection/move/', post({ card_id: cardId, source, target, quantity })),
  setNote: (cardId: number, location: number, notes: string) =>
    request<OwnedSummary>('/my-collection/note/', post({ card_id: cardId, location, notes })),
  locations: () => request<Location[]>('/my-collection/locations/'),
  createLocation: (name: string, kind: LocationKind) => request<Location>('/my-collection/locations/', post({ name, kind })),
  updateLocation: (id: number, changes: Partial<Pick<Location, 'name' | 'kind' | 'notes' | 'position'>>) =>
    request<Location>(`/my-collection/locations/${id}/`, { method: 'PATCH', body: JSON.stringify(changes) }),
  deleteLocation: (id: number) => request<void>(`/my-collection/locations/${id}/`, { method: 'DELETE' }),
}
