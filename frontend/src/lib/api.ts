import type {
  CardDetail, ChangesResponse, HistoryCard, CsvImportPreview, DeckDetail, DeckListCard, DeckVersion, RestorePlan, RestoreResult, DeckVersionDetail, FacetsResponse, FieldDef,
  KeywordSkillsResponse, Location, LocationKind, Match, MatchInput, OwnedSummary, RadarResponse, RestorePreview, SearchResponse,
} from './types'

import { csrfToken, reportApiFailure } from './errorReporter'

const BASE = import.meta.env.VITE_API_URL ?? '/api'

/** Descarga directa (enlace) de la copia de seguridad de Mi colección. */
export const COLLECTION_BACKUP_URL = `${BASE}/my-collection/backup/`
/** Descarga directa de Mi colección en CSV (para hojas de cálculo). */
export const COLLECTION_CSV_URL = `${BASE}/my-collection/csv/`

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
    headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrfToken(), ...(init?.headers ?? {}) },
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
    // Fallos del servidor y peticiones rechazadas: al registro de errores (y a Telegram).
    if (res.status >= 500 || res.status === 403) reportApiFailure(init?.method ?? 'GET', path, res.status, detail)
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
  /** Con scope 'collection': solo las cartas con copias falsas */
  fake?: boolean
  /** Con scope 'collection': contar también las copias falsas (por defecto, solo las auténticas) */
  include_fakes?: boolean
}

export type Scope = 'all' | 'collection'

export const api = {
  fields: () => request<FieldDef[]>('/fields/'),
  facets: (scope: Scope = 'all', location: number | null = null, includeFakes = false) =>
    request<FacetsResponse>(
      scope === 'collection'
        ? `/facets/?scope=collection${location ? `&location=${location}` : ''}${includeFakes ? '&include_fakes=true' : ''}`
        : '/facets/',
    ),
  facetsFor: (body: SearchBody & { only?: string[] }, signal?: AbortSignal) =>
    request<FacetsResponse>('/facets/', { method: 'POST', body: JSON.stringify(body), signal }),
  search: (body: SearchBody, signal?: AbortSignal) =>
    request<SearchResponse>('/cards/search/', { method: 'POST', body: JSON.stringify(body), signal }),
  card: (id: number) => request<CardDetail>(`/cards/${id}/`),
  keywordSkills: () => request<KeywordSkillsResponse>('/keyword-skills/'),
  /** Novedades: cambios reales detectados en los syncs. */
  changes: (kinds: string[] = [], page = 1) =>
    request<ChangesResponse>(`/changes/?page=${page}${kinds.length ? `&kind=${kinds.join(',')}` : ''}`),
  changesCount: (since: string | null) =>
    request<{ count: number; latest: string | null }>(`/changes/count/${since ? `?since=${encodeURIComponent(since)}` : ''}`),
  /** Mi colección: suma (delta > 0) o resta copias; sin `location`, + va a "Sin ubicar". */
  /** Mi colección: suma (delta > 0) o resta copias; sin `location`, + va a "Sin ubicar". `fake`: restar solo de falsas/auténticas. */
  adjustCollection: (cardId: number, delta: number, location?: number | null, fake?: boolean) =>
    request<OwnedSummary>(
      '/my-collection/adjust/',
      post({ card_id: cardId, delta, ...(location ? { location } : {}), ...(fake != null ? { fake } : {}) }),
    ),
  /** Mueve copias; misma ubicación y `targetFake` distinto = marcarlas como falsas o auténticas. */
  moveCopies: (
    cardId: number,
    source: number,
    target: number,
    quantity: number,
    sourceFake = false,
    targetFake?: boolean,
    noteLine?: string,
  ) =>
    request<OwnedSummary>(
      '/my-collection/move/',
      post({
        card_id: cardId,
        source,
        target,
        quantity,
        source_fake: sourceFake,
        ...(targetFake != null ? { target_fake: targetFake } : {}),
        ...(noteLine ? { note_line: noteLine } : {}),
      }),
    ),
  setNote: (cardId: number, location: number, notes: string, fake = false) =>
    request<OwnedSummary>('/my-collection/note/', post({ card_id: cardId, location, notes, fake })),
  /** «Mi orden»: esas cartas, en ese orden, dentro de la ubicación. */
  reorderCollection: (location: number, cardIds: number[]) =>
    request<void>('/my-collection/reorder/', post({ location, card_ids: cardIds })),
  /** Importar un CSV: sin `apply`, vista previa; con `apply`, suma las copias reconocidas. */
  previewCsvImport: (csv: string) => request<CsvImportPreview>('/my-collection/import/', post({ csv })),
  applyCsvImport: (csv: string) =>
    request<{ applied: CsvImportPreview['totals'] }>('/my-collection/import/', post({ csv, apply: true })),
  /** Restaurar la copia JSON SUSTITUYENDO la colección: sin `apply`, vista previa; con `apply`, la aplica. */
  previewRestore: (backup: unknown) => request<RestorePreview>('/my-collection/restore/', post({ backup })),
  applyRestore: (backup: unknown) =>
    request<{ applied: { copies: number; rows: number; created_locations: number; skipped: number } }>(
      '/my-collection/restore/', post({ backup, apply: true }),
    ),
  locations: () => request<Location[]>('/my-collection/locations/'),
  createLocation: (name: string, kind: LocationKind, position = 0) =>
    request<Location>('/my-collection/locations/', post({ name, kind, position })),
  updateLocation: (id: number, changes: Partial<Pick<Location, 'name' | 'kind' | 'notes' | 'position'>>) =>
    request<Location>(`/my-collection/locations/${id}/`, { method: 'PATCH', body: JSON.stringify(changes) }),
  /** Mazos al histórico: qué copias saldrían (GET) y pasarlo, con sus copias a «Sin ubicar» (POST). */
  deckHistoryPreview: (id: number) => request<{ deck: string; cards: HistoryCard[] }>(`/my-collection/decks/${id}/to-history/`),
  moveDeckToHistory: (id: number) =>
    request<{ deck: string; target: string; cards: HistoryCard[] }>(`/my-collection/decks/${id}/to-history/`, { method: 'POST' }),
  /** Un mazo del histórico vuelve a usarse; se trae una copia de su líder (null si no tienes ninguna). */
  deckBackInUse: (id: number) =>
    request<{ deck: string; leader: { card_number: string; name: string; from: string; fake: boolean } | null }>(
      `/my-collection/decks/${id}/back-in-use/`, { method: 'POST' }),
  /** El id de una carta a partir de su enlace (BT20-149, BT20-149-2 o el id de Bandai). */
  cardRef: (ref: string) => request<{ id: number; ref: string }>(`/cards/ref/${encodeURIComponent(ref)}/`),
  /** Radar de precios: lo que más sube y baja y lo más caro, en N días. */
  priceRadar: (days: number, scope: 'collection' | 'all') =>
    request<RadarResponse>(`/prices/radar/?days=${days}&scope=${scope}`),
  deleteLocation: (id: number) => request<void>(`/my-collection/locations/${id}/`, { method: 'DELETE' }),
  /** Mazos: lista actual, versiones guardadas y partidas. */
  deck: (id: number) => request<DeckDetail>(`/my-collection/decks/${id}/`),
  /** Guarda una lista: `cards` (la editada) o, sin ella, lo que hay en la caja. */
  saveDeckVersion: (deck: number, name = '', notes = '', cards?: DeckListCard[]) =>
    request<DeckVersion>(`/my-collection/decks/${deck}/versions/`, post({ name, notes, ...(cards ? { cards } : {}) })),
  /** Qué copias habría que mover para que la caja del mazo tenga esa lista. */
  deckPlan: (deck: number, cards: DeckListCard[]) => request<RestorePlan>(`/my-collection/decks/${deck}/plan/`, post({ cards })),
  deckVersion: (id: number) => request<DeckVersionDetail>(`/my-collection/deck-versions/${id}/`),
  updateDeckVersion: (id: number, changes: Partial<Pick<DeckVersion, 'name' | 'notes'>>) =>
    request<DeckVersion>(`/my-collection/deck-versions/${id}/`, { method: 'PATCH', body: JSON.stringify(changes) }),
  deleteDeckVersion: (id: number) => request<void>(`/my-collection/deck-versions/${id}/`, { method: 'DELETE' }),
  /** Hacer principal una versión: el plan de movimientos y ejecutarlo (las copias se mueven de verdad). */
  restorePlan: (id: number) => request<RestorePlan>(`/my-collection/deck-versions/${id}/restore/`),
  restoreVersion: (
    id: number,
    body: { default_target: number; targets: Record<number, number>; sources: Record<number, number> },
  ) => request<RestoreResult>(`/my-collection/deck-versions/${id}/restore/`, post(body)),
  /** Sin `version`: con la lista actual (si cambió desde la última versión, se guarda una nueva). */
  addMatch: (deck: number, match: MatchInput) => request<Match>(`/my-collection/decks/${deck}/matches/`, post(match)),
  updateMatch: (id: number, changes: Partial<MatchInput>) =>
    request<Match>(`/my-collection/matches/${id}/`, { method: 'PATCH', body: JSON.stringify(changes) }),
  deleteMatch: (id: number) => request<void>(`/my-collection/matches/${id}/`, { method: 'DELETE' }),
  /** Copias de esa carta del mazo que van al side deck. */
  setSide: (deck: number, cardId: number, quantity: number) =>
    request<{ bandai_id: number; side: number }>(`/my-collection/decks/${deck}/side/`, post({ bandai_id: cardId, quantity })),
}
