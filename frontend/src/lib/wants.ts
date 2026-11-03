// Wants (cartas que quiero comprar): las mismas en el buscador, la ficha y la página Wants. Se piden una vez
// ({id de carta: copias}) y cada cambio se ve al momento en todas partes.
import { useSyncExternalStore } from 'react'
import { api } from './api'

let wants: Record<number, number> | null = null
let loading = false
const listeners = new Set<() => void>()
const emit = () => listeners.forEach((l) => l())

function load() {
  if (wants || loading) return
  loading = true
  api
    .wantIds()
    .then((r) => {
      wants = r.wants
      emit()
    })
    .catch(() => {})
    .finally(() => {
      loading = false
    })
}

function subscribe(listener: () => void) {
  listeners.add(listener)
  load()
  return () => listeners.delete(listener)
}

/** {id de carta: copias que quiero}; null mientras llegan. */
export function useWants(): Record<number, number> | null {
  return useSyncExternalStore(subscribe, () => wants)
}

/** Cuántas copias quiero de esa carta (0 la quita). Se ve al momento; si falla, vuelve a como estaba. */
export async function setWant(id: number, quantity: number): Promise<void> {
  const before = wants?.[id] ?? 0
  const put = (n: number) => {
    const next = { ...(wants ?? {}) }
    if (n > 0) next[id] = n
    else delete next[id]
    wants = next
    emit()
  }
  put(quantity)
  try {
    await api.setWant(id, quantity)
  } catch (e) {
    put(before)
    throw e
  }
}
