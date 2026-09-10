import type { CardDetail, FacetsResponse, FieldDef, SearchResponse } from './types'

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
}

export const api = {
  fields: () => request<FieldDef[]>('/fields/'),
  facets: () => request<FacetsResponse>('/facets/'),
  facetsFor: (body: SearchBody & { only?: string[] }, signal?: AbortSignal) =>
    request<FacetsResponse>('/facets/', { method: 'POST', body: JSON.stringify(body), signal }),
  search: (body: SearchBody, signal?: AbortSignal) =>
    request<SearchResponse>('/cards/search/', { method: 'POST', body: JSON.stringify(body), signal }),
  card: (id: number) => request<CardDetail>(`/cards/${id}/`),
}
