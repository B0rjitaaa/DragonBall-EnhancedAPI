export type FieldType = 'text' | 'number' | 'enum' | 'array' | 'boolean'

export interface FieldDef {
  key: string
  label: string
  type: FieldType
  group: string
  operators: string[]
  facet: boolean
}

export interface FacetValue {
  value: string | number
  count: number
}

export interface Facet {
  values: FacetValue[]
  min?: number | null
  max?: number | null
}

export interface FacetsResponse {
  total: number
  facets: Record<string, Facet>
}

export interface Condition {
  id: string
  field: string
  operator: string
  value: unknown
  not?: boolean
}

export interface Group {
  id: string
  op: 'and' | 'or'
  not?: boolean
  children: QueryNode[]
}

export type QueryNode = Condition | Group

export const isGroup = (n: QueryNode): n is Group => 'children' in n

export interface CardSummary {
  id: number
  card_number: string
  name: string
  image_url: string
  card_type: string
  colors: string[]
  rarity: string
  rarity_code: string
  energy: number | null
  power: number | null
  set_code: string
  card_set: string
  has_back: boolean
  back_name: string
  back_image_url: string
  legality: 'legal' | 'limited' | 'banned'
  legality_since: string
  keyword_skills: string[]
  /** Solo en Mi colección: copias (las de la ubicación filtrada, si hay filtro) y su reparto. */
  quantity?: number
  /** Con filtro de ubicación: copias en total, en todas las ubicaciones. */
  total_quantity?: number
  /** Copias falsas (en total). */
  fakes?: number
  locations?: OwnedLocation[]
}

export type LocationKind = 'deck' | 'binder' | 'storage' | 'other'

/** Copias de una carta en una ubicación (las falsas van en su propia fila). */
export interface OwnedLocation {
  id: number
  name: string
  kind: LocationKind
  quantity: number
  fake: boolean
  notes: string
}

/** Ubicación de Mi colección (mazo, archivador, almacén…) con sus totales. */
export interface Location {
  id: number
  name: string
  kind: LocationKind
  notes: string
  is_default: boolean
  position: number
  cards: number
  copies: number
  fakes: number
  /** Solo en mazos: su carta Líder, con la imagen de la cara despertada. */
  leader?: DeckLeader | null
}

export interface DeckLeader {
  id: number
  card_number: string
  name: string
  image: string
  awakened: boolean
}

/** Respuesta de las operaciones de Mi colección sobre una carta. */
export interface OwnedSummary {
  card_id: number
  quantity: number
  fakes: number
  locations: OwnedLocation[]
}

export interface CardDetail extends CardSummary {
  text: string
  back_text: string
  back_power: number | null
  series: string
  color_cost: string
  combo_energy: number | null
  combo_power: number | null
  z_energy_cost: number | null
  characters: string[]
  special_traits: string[]
  eras: string[]
  notes: string
  keywords: string[]
  keyword_families: string[]
  keyword_mentions: string[]
  timing: string[]
  keyword_rules: string[]
  regulations: string[]
  config: Record<string, string | null>
  back_config: Record<string, string | null>
}

export interface SearchResponse {
  count: number
  page: number
  page_size: number
  pages: number
  results: CardSummary[]
  /** Solo en Mi colección */
  total_copies?: number
  missing?: string[]
}

/** Estado del panel facetado: valores marcados (OR / AND) o rango numérico por campo. */
export interface FacetSelection {
  values: (string | number)[]
  match: 'any' | 'all'
  min?: number | ''
  max?: number | ''
}

export type FacetState = Record<string, FacetSelection>

export type SkillCategory = 'timing' | 'skill' | 'keyword'

export interface KeywordSkill {
  name: string
  category: SkillCategory
  description: string
  order: number
}

export interface KeywordSkillsResponse {
  updated: string
  source: string
  skills: KeywordSkill[]
  /** 'Over Realm X' -> [{value: 'Over Realm 3', count}, …] */
  variants: Record<string, FacetValue[]>
  /** habilidad normalizada ('Once Per Turn', 'Over Realm 3') -> nombre oficial */
  aliases: Record<string, string>
  deck_rules: Record<string, string>
}

