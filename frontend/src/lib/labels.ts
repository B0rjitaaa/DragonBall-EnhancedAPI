export const LEGALITY_LABELS: Record<string, string> = {
  banned: 'Banned',
  limited: 'Limited',
  legal: 'Legal',
}

const VALUE_LABELS: Record<string, Record<string, string>> = { legality: LEGALITY_LABELS }

/** Texto a mostrar para un valor de faceta (los códigos internos se traducen). */
export function valueLabel(field: string, value: unknown): string {
  return VALUE_LABELS[field]?.[String(value)] ?? String(value)
}
