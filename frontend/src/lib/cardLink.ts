import { useCallback, useEffect, useState } from 'react'
import { api } from './api'

/** Enlace a una carta: `?card=BT20-149` (su primera impresión), `?card=BT20-149-2`… (las siguientes,
 * por orden de alta), en cualquier página que abre el detalle (Buscador, Mi colección, Novedades,
 * Precios). Los enlaces antiguos con el id de Bandai (`?card=54229`) siguen valiendo. */
export const CARD_PARAM = 'card'

const cardParam = () => new URLSearchParams(window.location.search).get(CARD_PARAM)

function setCardInUrl(ref: string | null): void {
  const url = new URL(window.location.href)
  if (ref == null) url.searchParams.delete(CARD_PARAM)
  else url.searchParams.set(CARD_PARAM, ref)
  window.history.replaceState(null, '', `${url.pathname}${url.search}${url.hash}`)
}

/** Ya abierta la carta, la dirección pasa a llevar su número (también si se abrió por id). */
export function showCardRef(ref: string): void {
  if (cardParam() !== ref) setCardInUrl(ref)
}

/** Enlace completo para compartir: la página actual con la carta abierta. */
export function cardLink(ref: string): string {
  const url = new URL(window.location.href)
  url.searchParams.set(CARD_PARAM, ref)
  return url.toString()
}

/** Carta abierta en el detalle, enlazada con la dirección (la de `?card=` al cargar la página). */
export function useOpenCard(): [number | null, (id: number | null) => void] {
  const [openId, setOpenId] = useState<number | null>(null)
  useEffect(() => {
    const ref = cardParam()
    if (!ref) return
    api
      .cardRef(ref)
      .then((r) => setOpenId(r.id))
      .catch(() => setCardInUrl(null)) // número que no existe: se quita de la dirección
  }, [])
  const open = useCallback((id: number | null) => {
    setOpenId(id)
    // Al abrir, el id hasta que el detalle carga y pone el número; al cerrar, nada.
    setCardInUrl(id == null ? null : String(id))
  }, [])
  return [openId, open]
}
