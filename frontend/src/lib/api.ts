import type { CardDetail, FacetsResponse, FieldDef, KeywordSkillsResponse, SearchResponse } from './types'

const BASE = import.meta.env.VITE_API_URL ?? '/api'

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    ...init,
    headers: { 'Content-Type': 'application/json', ...(init?.headers ?? {}) },
  })
  if (!res.ok) {
    let detail = `${res.status} ${res.statusText}`
    try {
      const body = await res.json()
      detail = typeof body === 'object' ? Object.values(body).flat().join(' · ') : String(body)
    } catch {
      /* respuesta sin JSON */
    }
    throw new Error(detail)
  }
  return res.json() as Promise<T>
}

export interface SearchBody {
  q?: string
  query?: unknown
  ordering?: string
  page?: number
  page_size?: number
  /** 'collection': solo las cartas de Mi colección */
  scope?: Scope
}

export type Scope = 'all' | 'collection'

export const api = {
  fields: () => request<FieldDef[]>('/fields/'),
  facets: (scope: Scope = 'all') => request<FacetsResponse>(scope === 'collection' ? '/facets/?scope=collection' : '/facets/'),
  facetsFor: (body: SearchBody & { only?: string[] }, signal?: AbortSignal) =>
    request<FacetsResponse>('/facets/', { method: 'POST', body: JSON.stringify(body), signal }),
  search: (body: SearchBody, signal?: AbortSignal) =>
    request<SearchResponse>('/cards/search/', { method: 'POST', body: JSON.stringify(body), signal }),
  card: (id: number) => request<CardDetail>(`/cards/${id}/`),
  keywordSkills: () => request<KeywordSkillsResponse>('/keyword-skills/'),
  /** Mi colección: suma (delta > 0) o resta copias de una carta en la colección del escáner. */
  adjustCollection: (cardId: number, delta: number) =>
    request<{ card_id: number; quantity: number; conditions: Record<string, number> }>('/my-collection/adjust/', {
      method: 'POST',
      body: JSON.stringify({ card_id: cardId, delta }),
    }),
}
