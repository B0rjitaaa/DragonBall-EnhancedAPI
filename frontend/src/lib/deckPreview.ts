import type { CardSummary, DeckImportPreview, DeckImportRow } from './types'

/** Las cartas del mazo tal como quedaría: Leader, Main y Z juntos (la vista los separa por tipo) y el side aparte.
 *  Las que faltan se apuntan primero en el side, igual que al crear el mazo. */
export function previewDeckCards(preview: DeckImportPreview | null, missingOf: (r: DeckImportRow) => number = (r) => r.missing) {
  const pool: CardSummary[] = []
  const side: CardSummary[] = []
  for (const r of preview?.rows ?? []) {
    const card = preview?.catalog[r.bandai_id]
    if (!card) continue
    const inSide = r.sections.side ?? 0
    const inDeck = (r.sections.leader ?? 0) + (r.sections.main ?? 0) + (r.sections.z ?? 0)
    const lack = missingOf(r)
    const sideLack = Math.min(lack, inSide)
    if (inDeck) pool.push({ ...card, quantity: inDeck, missing: Math.min(lack - sideLack, inDeck) } as CardSummary)
    if (inSide) side.push({ ...card, quantity: inSide, missing: sideLack } as CardSummary)
  }
  return { pool, side }
}
