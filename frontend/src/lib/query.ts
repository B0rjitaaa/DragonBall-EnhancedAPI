import type { Condition, FacetState, FieldDef, Group, QueryNode } from './types'
import { isGroup } from './types'

let seq = 0
export const uid = () => `n${Date.now().toString(36)}${(seq++).toString(36)}`

export const OPERATOR_LABELS: Record<string, string> = {
  contains: 'contiene',
  eq: 'es',
  startswith: 'empieza por',
  ne: '≠',
  lt: '<',
  lte: '≤',
  gt: '>',
  gte: '≥',
  between: 'entre',
  isnull: 'sin valor',
  in: 'es uno de',
  has: 'incluye',
  has_any: 'incluye alguno de',
  has_all: 'incluye todos',
  is_empty: 'está vacío',
}

export function defaultValue(field: FieldDef, operator: string): unknown {
  if (operator === 'between') return ['', '']
  if (['in', 'has_any', 'has_all'].includes(operator)) return []
  if (operator === 'isnull' || operator === 'is_empty' || field.type === 'boolean') return true
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
}

export function readUrlState(): Partial<UrlState> {
  try {
    const raw = decodeURIComponent(window.location.hash.slice(1))
    return raw ? (JSON.parse(raw) as Partial<UrlState>) : {}
  } catch {
    return {}
  }
}

export function writeUrlState(state: UrlState): void {
  const empty =
    !state.q && !Object.keys(state.facets).length && !state.advanced.children.length && state.page === 1
  const hash = empty && state.ordering === 'number' ? '' : `#${encodeURIComponent(JSON.stringify(state))}`
  window.history.replaceState(null, '', `${window.location.pathname}${window.location.search}${hash}`)
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
