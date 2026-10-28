export type FieldType = 'text' | 'number' | 'enum' | 'array' | 'boolean' | 'flag'

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

/** Precio de Cardmarket en € (ver backend/prices). */
export interface CardPrice {
  /** Precio de la carta: trend (corregido si se dispara), la media de 30 días o, sin ventas, el anuncio más barato. */
  eur: number
  /** Es solo el anuncio más barato (carta sin ventas recientes): menos fiable. */
  is_low: boolean
  /** Precio puesto a mano en la revisión (ningún producto de Cardmarket era el bueno). */
  manual: boolean
  /** Precio dudoso (solo un anuncio, muy caro para su rareza): no cuenta en el valor hasta revisarlo. */
  suspect: boolean
  /** Cuenta en el valor de la colección (con ventas, a mano o confirmado en la revisión). */
  counts: boolean
  trend: number | null
  avg30: number | null
  low: number | null
  /** La carta en Cardmarket, con las ofertas de toda Europa (de donde sale el precio). */
  url: string
  /** La misma, solo con vendedores de España (suelen ser menos y más caros). */
  url_es: string
}

/** Valor de las copias auténticas que se ven en Mi colección. */
export interface CollectionValue {
  /** Lo que tiene ventas en Cardmarket (o precio confirmado o a mano). */
  value: number
  /** Aparte, sin sumar: cartas sin ventas, por lo que pide un vendedor. */
  value_listing: number
  copies_priced: number
  copies_listing: number
  copies_unpriced: number
}

export interface CardSummary {
  id: number
  card_number: string
  name: string
  image_url: string
  /** Miniatura (WebP, 320 px) para cuadrículas y listas; la ficha usa image_url. */
  thumb_url?: string
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
  /** Tiene errata oficial. */
  has_errata: boolean
  /** Número de preguntas/respuestas oficiales (Card Q&A). */
  rulings_count: number
  /** Precio en Cardmarket, o null si no está emparejada o no tiene datos. */
  price?: CardPrice | null
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
  /** Identificador para enlaces (/collection/deck/<uid>). */
  uid: string
  name: string
  kind: LocationKind
  /** Solo cuenta en los mazos: «parked» = en el histórico (sus copias pasan a «Sin ubicar»). */
  status: LocationStatus
  /** Desde cuándo está en el histórico (ISO), o null. */
  parked_at: string | null
  notes: string
  is_default: boolean
  position: number
  cards: number
  copies: number
  fakes: number
  /** Solo en mazos: su carta Líder, con la imagen de la cara despertada. */
  leader?: DeckLeader | null
  /** Solo en mazos con problemas: prohibidas y limitadas con más de una copia (números de carta). */
  issues?: { banned: string[]; limited: string[] } | null
  /** Solo en mazos del histórico: copias de su última lista guardada. */
  last_list?: number | null
  /** Valor en € de sus copias auténticas (Cardmarket). */
  value?: number
  /** Solo en mazos: cada vez que pasó al histórico o volvió a usarse, del más reciente al más antiguo. */
  status_log?: StatusChange[]
}

/** Un paso de un mazo al histórico (con las copias que salieron) o su vuelta a usarse. */
export interface StatusChange {
  status: LocationStatus
  at: string
  copies: number
}

/** Copias de un mazo que van (o han ido) a «Sin ubicar» al pasarlo al histórico. */
export interface HistoryCard {
  bandai_id: number
  card_number: string
  name: string
  card_type: string
  image: string
  quantity: number
  fake: boolean
}

export type LocationStatus = 'active' | 'parked'

export interface DeckLeader {
  id: number
  card_number: string
  name: string
  image: string
  awakened: boolean
  colors: string[]
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
  /** Errata oficial de la carta (null si no tiene). */
  errata: CardErrataInfo | null
  /** Preguntas y respuestas oficiales (Card Q&A). */
  rulings: CardRuling[]
}

/** Un cambio real detectado al sincronizar (carta nueva, texto, banlist, errata…). */
export interface CardChange {
  id: number
  kind: 'new' | 'text' | 'image' | 'stats' | 'banned' | 'limited' | 'legal' | 'errata' | 'ruling'
  kind_label: string
  created_at: string
  card_id: number | null
  card_number: string
  card_name: string
  thumb_url: string
  field: string
  before: string
  after: string
}

export interface ChangesResponse {
  count: number
  page: number
  pages: number
  kinds: { kind: CardChange['kind']; label: string; count: number }[]
  results: CardChange[]
}

/** Vista previa de importar Mi colección desde CSV (nunca borra: solo suma copias). */
export interface CsvImportPreview {
  rows: {
    line: number
    card_id: number
    card_number: string
    name: string
    location: string
    unknown_location: string
    qty: number
    fake: boolean
    notes: string
  }[]
  errors: { line: number; reason: string }[]
  ambiguous: { line: number; number: string; qty: number; options: { id: number; card_set: string }[] }[]
  totals: { rows: number; copies: number; fakes: number; unknown_locations: string[]; skipped: number }
}

export interface CardErrataInfo {
  card_name: string
  before: string
  after: string
  notes: string
  image_url: string
  date: string
  list_updated: string
}

export interface CardRuling {
  order: number
  question: string
  answer: string
  is_new: boolean
  set_label: string
}

export interface SearchResponse {
  count: number
  page: number
  page_size: number
  pages: number
  results: CardSummary[]
  /** Solo en Mi colección */
  total_copies?: number
  /** Solo en Mi colección: valor de las copias auténticas que se ven (con los filtros). */
  value?: CollectionValue
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


/** Mazos: listas (versiones) y partidas. Las cartas van por su id de Bandai (= CardSummary.id). */
export type DeckSection = 'main' | 'z' | 'side'
export type MatchResult = 'win' | 'loss' | 'draw'

export interface DeckListCard {
  bandai_id: number
  section: DeckSection
  quantity: number
}

export interface DeckChange {
  bandai_id: number
  section: DeckSection
  delta: number
}

export interface MatchRecord {
  played: number
  wins: number
  losses: number
  draws: number
  win_rate: number | null
}

export interface LeaderRecord extends MatchRecord {
  leader_bandai_id: number | null
  leader_name: string
}

export interface DeckVersion {
  id: number
  number: number
  name: string
  notes: string
  /** Guardada sola al anotar la primera partida (con lo que había en la caja). */
  automatic: boolean
  /** La lista principal: la de la caja, con la que se anotan las partidas. */
  principal: boolean
  created_at: string
}

export interface Match {
  id: number
  version: number
  played_on: string
  opponent_leader_bandai_id: number | null
  opponent_leader_name: string
  opponent_name: string
  result: MatchResult
  went_first: boolean | null
  score: string
  event: string
  notes: string
  created_at: string
  /** En la vista del mazo: número de la versión con la que se jugó. */
  version_number?: number
}

export type MatchInput = Omit<Match, 'id' | 'version' | 'created_at' | 'version_number'> & { version?: number }

export interface DeckDetail {
  deck: { id: number; name: string }
  /** Lo que hay en la caja del mazo. */
  current: DeckListCard[]
  /** Id de la lista principal. */
  principal: number | null
  /** Número de la lista con la que se compara la caja (la principal o, si no hay, la última). */
  compared_to: number | null
  /** Lo que hay en la caja frente a esa lista. */
  changes: DeckChange[]
  versions: (DeckVersion & { record: MatchRecord; copies: number })[]
  matches: Match[]
  record: MatchRecord
  by_leader: LeaderRecord[]
  /** Datos de catálogo de todas las cartas que aparecen. */
  catalog: Record<number, CardSummary>
}

export interface DeckVersionDetail extends DeckVersion {
  deck: number
  cards: DeckListCard[]
  previous: number | null
  changes: DeckChange[]
  matches: Match[]
  record: MatchRecord
  by_leader: LeaderRecord[]
  catalog: Record<number, CardSummary>
}

/** Hacer principal una versión: qué copias salen del mazo y cuáles entran (y de dónde). */
export interface RestoreSource {
  id: number
  name: string
  kind: LocationKind
  is_default: boolean
  authentic: number
  fakes: number
}

export interface RestorePlan {
  version?: number
  default_target: { id: number; name: string; kind: LocationKind; is_default: boolean }
  outgoing: { bandai_id: number; quantity: number; fakes: number }[]
  incoming: { bandai_id: number; quantity: number; missing: number; sources: RestoreSource[] }[]
  catalog: Record<number, CardSummary>
}

export interface RestoreResult {
  moved_out: number
  moved_in: number
  missing: { bandai_id: number; quantity: number }[]
}

/** Imagen para cuadrículas y listas: la miniatura si la hay, si no la original. */
export const cardThumb = (card: Pick<CardSummary, 'image_url' | 'thumb_url'>): string => card.thumb_url || card.image_url
