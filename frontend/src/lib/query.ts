import { CARD_PARAM } from './cardLink'
import type { Condition, FacetState, FieldDef, Group, QueryNode } from './types'
import { isGroup } from './types'

let seq = 0
export const uid = () => `n${Date.now().toString(36)}${(seq++).toString(36)}`

export const OPERATOR_LABELS: Record<string, string> = {
  contains: 'contains',
  eq: 'is',
  startswith: 'starts with',
  ne: '≠',
  lt: '<',
  lte: '≤',
  gt: '>',
  gte: '≥',
  between: 'between',
  isnull: 'has no value',
  in: 'is one of',
  has: 'includes',
  has_any: 'includes any of',
  has_all: 'includes all',
  is_empty: 'is empty',
}

export function defaultValue(field: FieldDef, operator: string): unknown {
  if (operator === 'between') return ['', '']
  if (['in', 'has_any', 'has_all'].includes(operator)) return []
  if (operator === 'isnull' || operator === 'is_empty' || field.type === 'boolean' || field.type === 'flag') return true
  return ''
}

export function newCondition(field: FieldDef): Condition {
  const operator = field.operators[0]
  return { id: uid(), field: field.key, operator, value: defaultValue(field, operator) }
}

export const newGroup = (op: 'and' | 'or' = 'and', children: QueryNode[] = []): Group => ({
  id: uid(),
  op,
  children,
})

/** Sustituye (o elimina si fn devuelve null) el nodo con ese id dentro del árbol. */
export function updateNode(root: Group, id: string, fn: (n: QueryNode) => QueryNode | null): Group {
  const walk = (node: QueryNode): QueryNode | null => {
    if (node.id === id) return fn(node)
    if (!isGroup(node)) return node
    return { ...node, children: node.children.map(walk).filter((c): c is QueryNode => c !== null) }
  }
  return (walk(root) as Group | null) ?? newGroup()
}

function isComplete(c: Condition): boolean {
  const v = c.value
  if (c.operator === 'between') return Array.isArray(v) && v.some((x) => x !== '' && x !== null)
  if (Array.isArray(v)) return v.length > 0
  return v !== '' && v !== null && v !== undefined
}

/** Árbol limpio para el backend: sin ids ni condiciones a medio rellenar ni grupos vacíos. */
export function toApiTree(node: QueryNode): Record<string, unknown> | null {
  if (isGroup(node)) {
    const children = node.children.map(toApiTree).filter(Boolean)
    if (!children.length) return null
    return { op: node.op, not: !!node.not, children }
  }
  if (!isComplete(node)) return null
  return { field: node.field, operator: node.operator, value: node.value, not: !!node.not }
}

export function facetsToConditions(state: FacetState, fields: FieldDef[]): Record<string, unknown>[] {
  const byKey = Object.fromEntries(fields.map((f) => [f.key, f]))
  const out: Record<string, unknown>[] = []
  for (const [key, sel] of Object.entries(state)) {
    const f = byKey[key]
    if (!f) continue
    if (f.type === 'number') {
      if (sel.values.length) {
        out.push({ op: 'or', children: sel.values.map((v) => ({ field: key, operator: 'eq', value: v })) })
      }
      const lo = sel.min ?? ''
      const hi = sel.max ?? ''
      if (lo !== '' || hi !== '') out.push({ field: key, operator: 'between', value: [lo, hi] })
    } else if (f.type === 'flag') {
      if (sel.values.length) out.push({ field: key, operator: 'eq', value: true })
    } else if (sel.values.length) {
      if (f.type === 'array') {
        out.push({ field: key, operator: sel.match === 'all' ? 'has_all' : 'has_any', value: sel.values })
      } else {
        out.push({ field: key, operator: 'in', value: sel.values })
      }
    }
  }
  return out
}

export function buildQuery(
  facets: FacetState,
  advanced: Group,
  advancedOn: boolean,
  fields: FieldDef[],
): Record<string, unknown> | null {
  const children = facetsToConditions(facets, fields)
  const adv = advancedOn ? toApiTree(advanced) : null
  if (adv) children.push(adv)
  return children.length ? { op: 'and', children } : null
}

export function countActive(state: FacetState): number {
  return Object.values(state).reduce(
    (n, s) => n + s.values.length + (s.min !== undefined && s.min !== '' ? 1 : 0) + (s.max !== undefined && s.max !== '' ? 1 : 0),
    0,
  )
}

// --- Estado compartible en la URL (#...) -------------------------------------------

export interface UrlState {
  q: string
  facets: FacetState
  advanced: Group
  advancedOn: boolean
  ordering: string
  page: number
  /** Mi colección: ubicación filtrada */
  location?: number | null
  /** Mi colección: cuadrícula o lista */
  view?: 'grid' | 'list' | 'deck'
  /** Mi colección: contar y mostrar también las copias falsas */
  showFakes?: boolean
}

/** Lo que se lee de la URL: el estado, y la ubicación por su uid (se resuelve a su id al cargar las ubicaciones). */
export type InitialUrlState = Partial<UrlState> & { locationUid?: string }

const LOCATION_PATH = /^\/collection\/(deck|location)\/([0-9a-f-]{36})\/?$/i

/** Ruta de Mi colección dentro de una ubicación: /collection/deck/<uid> o /collection/location/<uid>. */
export function locationPath(loc: { uid: string; kind: string }): string {
  return `/collection/${loc.kind === 'deck' ? 'deck' : 'location'}/${loc.uid}`
}

const parseJson = <T,>(raw: string | null): T | undefined => {
  if (!raw) return undefined
  try {
    return JSON.parse(raw) as T
  } catch {
    return undefined
  }
}

/**
 * Estado de la búsqueda desde la URL: la ubicación va en la ruta y lo demás en
 * parámetros legibles (?q=goku&sort=-energy&page=2…), solo lo que no es por defecto.
 * Los enlaces antiguos (todo en JSON tras el #) se siguen entendiendo.
 */
export function readUrlState(): InitialUrlState {
  const legacy = parseJson<Partial<UrlState>>(decodeURIComponent(window.location.hash.slice(1)))
  if (legacy) return legacy
  const params = new URLSearchParams(window.location.search)
  const state: InitialUrlState = {}
  const match = window.location.pathname.match(LOCATION_PATH)
  if (match) state.locationUid = match[2].toLowerCase()
  if (params.get('q')) state.q = params.get('q')!
  if (params.get('sort')) state.ordering = params.get('sort')!
  else if (match) state.ordering = 'position'
  const page = Number(params.get('page'))
  if (page > 1) state.page = page
  const view = params.get('view')
  if (view === 'grid' || view === 'list' || view === 'deck') state.view = view
  // /collection/deck/<uid>: ya se sabe que es un mazo, se empieza en la vista Mazo
  // (si no, se buscaba primero en cuadrícula y otra vez al cambiar de vista).
  else if (match?.[1].toLowerCase() === 'deck') state.view = 'deck'
  if (params.get('fakes') === '1') state.showFakes = true
  const facets = parseJson<FacetState>(params.get('filters'))
  if (facets) state.facets = facets
  const advanced = parseJson<Group>(params.get('advanced'))
  if (advanced) {
    state.advanced = advanced
    state.advancedOn = params.get('advanced_on') !== '0'
  }
  return state
}

/** Escribe el estado en la URL (sin recargar). `loc`: la ubicación filtrada, si la hay y ya se conoce. */
export function writeUrlState(state: UrlState, loc?: { uid: string; kind: string } | null): void {
  const params = new URLSearchParams()
  const defaultOrdering = loc ? 'position' : 'number'
  const defaultView = loc?.kind === 'deck' ? 'deck' : 'grid'
  if (state.q) params.set('q', state.q)
  if (state.ordering !== defaultOrdering) params.set('sort', state.ordering)
  if (state.page > 1 && state.view !== 'deck') params.set('page', String(state.page))
  if ((state.view ?? 'grid') !== defaultView) params.set('view', state.view ?? 'grid')
  if (state.showFakes) params.set('fakes', '1')
  if (Object.keys(state.facets).length) params.set('filters', JSON.stringify(state.facets))
  if (state.advanced.children.length) {
    params.set('advanced', JSON.stringify(state.advanced))
    if (!state.advancedOn) params.set('advanced_on', '0')
  }
  // La carta abierta (enlace ?card=) no es parte de la búsqueda: se conserva.
  const card = new URLSearchParams(window.location.search).get(CARD_PARAM)
  if (card) params.set(CARD_PARAM, card)
  const inCollection = window.location.pathname.startsWith('/collection')
  const path = !inCollection ? window.location.pathname : loc ? locationPath(loc) : '/collection'
  const search = params.toString()
  window.history.replaceState(null, '', `${path}${search ? `?${search}` : ''}`)
}

// Misma normalización que el backend (cards/parsing.py) para que '[Activate : Main]' del texto
// coincida con la habilidad guardada 'Activate: Main'.
const JP_COLORS: Record<string, string> = { 赤: 'Red', 青: 'Blue', 緑: 'Green', 黄: 'Yellow', 黒: 'Black', 白: 'White' }
const KEYWORD_ALIASES: Record<string, string> = {
  'Doube Strike': 'Double Strike',
  'Energy Exhaust': 'Energy-Exhaust',
  'Union Potara': 'Union-Potara',
}

export function normalizeKeyword(raw: string): string {
  let s = raw.normalize('NFKC')
  for (const [jp, en] of Object.entries(JP_COLORS)) s = s.split(jp).join(en)
  s = s
    .replace(/\((\w+)\)/g, '$1')
    .replace(/(?<=[a-z])(?=\d)/g, ' ')
    .replace(/\s+/g, ' ')
    .trim()
    .replace(/\s*:\s*/g, ': ')
    .replace(/\s*\/\s*/g, '/')
    .replace(/(?<![A-Za-z])([a-z])([a-z]*)/g, (_, a: string, b: string) => a.toUpperCase() + b)
    .replace(/^(Activate|Counter) (?=[A-Z])/, '$1: ')
  return KEYWORD_ALIASES[s] ?? s
}

