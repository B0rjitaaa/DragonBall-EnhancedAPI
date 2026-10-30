import type { CardSummary } from './types'

/**
 * Exportar un mazo fuera de la web:
 * - a Time Chamber (simulador online de DBS Masters): abre su importador con la lista en la
 *   dirección, igual que hace DeckPlanet. Formato comprobado a mano:
 *   https://time-chamber.net/decks/import?leader=BT14-002&main=BT14-018x4,…&z=EX23-02x4&side=BT5-023x2
 * - como texto (el formato de DeckPlanet): para pegarlo en TCGArena, Discord, etc.
 * Las impresiones de una carta (alt art…) comparten número: se juntan y se suman sus copias.
 */

const TIME_CHAMBER_IMPORT = 'https://time-chamber.net/decks/import'

export interface ExportDeck {
  leader?: CardSummary
  main: CardSummary[]
  z: CardSummary[]
  side: CardSummary[]
}

interface Line {
  number: string
  name: string
  quantity: number
}

/** Una línea por número de carta, ordenadas por número (BT2 antes que BT10). */
function lines(cards: CardSummary[]): Line[] {
  const byNumber = new Map<string, Line>()
  for (const c of cards) {
    const n = c.quantity ?? 1
    const line = byNumber.get(c.card_number)
    if (line) line.quantity += n
    else byNumber.set(c.card_number, { number: c.card_number, name: c.name, quantity: n })
  }
  return [...byNumber.values()]
    .filter((l) => l.quantity > 0)
    .sort((a, b) => a.number.localeCompare(b.number, 'en', { numeric: true }))
}

export function isExportable(deck: ExportDeck): boolean {
  return Boolean(deck.leader || deck.main.length || deck.z.length || deck.side.length)
}

/** Dirección del importador de Time Chamber con el mazo (Leader, Main, Z y Side). */
export function timeChamberUrl(deck: ExportDeck): string {
  const params = new URLSearchParams()
  if (deck.leader) params.set('leader', deck.leader.card_number)
  const part = (cards: CardSummary[]) => lines(cards).map((l) => `${l.number}x${l.quantity}`).join(',')
  for (const [key, cards] of [['main', deck.main], ['z', deck.z], ['side', deck.side]] as const) {
    const value = part(cards)
    if (value) params.set(key, value)
  }
  return `${TIME_CHAMBER_IMPORT}?${params}`
}

/** La lista en texto, por secciones: «4 Jiren, the Avenger [BT14-018]». */
export function deckListText(deck: ExportDeck): string {
  const out: string[] = []
  const section = (title: string, rows: string[]) => {
    if (!rows.length) return
    if (out.length) out.push('')
    out.push(`_____${title}_____`, ...rows)
  }
  if (deck.leader) {
    const { name, back_name, card_number } = deck.leader
    section('Leader', [`${back_name && back_name !== name ? `${name} // ${back_name}` : name} [${card_number}]`])
  }
  const rows = (cards: CardSummary[]) => lines(cards).map((l) => `${l.quantity} ${l.name} [${l.number}]`)
  section('Main Deck', rows(deck.main))
  section('Z Deck', rows(deck.z))
  section('Side Deck', rows(deck.side))
  return `${out.join('\n')}\n`
}
