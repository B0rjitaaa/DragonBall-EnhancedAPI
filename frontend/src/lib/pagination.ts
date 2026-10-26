/** Un número de página o un hueco («…») en la paginación. */
export type PageItem = number | 'gap'

/**
 * Qué páginas enseñar: siempre la primera y la última, la actual y `siblings` a cada
 * lado, y «…» en los huecos. Siempre salen los mismos botones (2·siblings + 5), así la
 * barra no cambia de ancho al moverse; si caben todas las páginas, salen todas.
 */
export function pageItems(current: number, total: number, siblings = 1): PageItem[] {
  const slots = 2 * siblings + 5
  if (total <= slots) return Array.from({ length: total }, (_, i) => i + 1)
  const range = (from: number, to: number) => Array.from({ length: to - from + 1 }, (_, i) => from + i)
  // Cerca del principio o del final: un solo hueco.
  if (current <= siblings + 3) return [...range(1, slots - 2), 'gap', total]
  if (current >= total - siblings - 2) return [1, 'gap', ...range(total - (slots - 3), total)]
  return [1, 'gap', ...range(current - siblings, current + siblings), 'gap', total]
}
