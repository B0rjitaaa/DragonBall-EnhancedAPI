/** Páginas de archivador: bolsillos por página (filas × columnas). Lo usan las ubicaciones tipo Binder y el
 * modo archivador del escáner. El backend admite hasta BINDER_MAX_SIDE por lado. */

export const BINDER_MAX_SIDE = 6

export interface BinderSize {
  rows: number
  cols: number
}

export const DEFAULT_BINDER: BinderSize = { rows: 3, cols: 3 }

/** Los tamaños habituales, en el orden en que se ofrecen. */
export const BINDER_PRESETS: BinderSize[] = [
  { rows: 2, cols: 2 },
  { rows: 3, cols: 3 },
  { rows: 4, cols: 3 },
  { rows: 4, cols: 4 },
]

/** «3×4 · 12 pockets» (columnas × filas, como se nombran los archivadores). */
export function binderLabel({ rows, cols }: BinderSize, withPockets = true): string {
  return `${cols}×${rows}${withPockets ? ` · ${rows * cols} pockets` : ''}`
}

export function isPreset({ rows, cols }: BinderSize): boolean {
  return BINDER_PRESETS.some((p) => p.rows === rows && p.cols === cols)
}

export function clampSide(n: number): number {
  return Math.max(1, Math.min(BINDER_MAX_SIDE, Math.round(n) || 1))
}
