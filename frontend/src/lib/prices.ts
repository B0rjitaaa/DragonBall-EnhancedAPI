import type { CardPrice } from './types'

const EUR = new Intl.NumberFormat('es-ES', { style: 'currency', currency: 'EUR' })
const EUR_ROUND = new Intl.NumberFormat('es-ES', { style: 'currency', currency: 'EUR', maximumFractionDigits: 0 })

/** 11,60 € (y sin decimales a partir de 1.000 €, para los totales). */
export const formatEur = (n: number) => (Math.abs(n) >= 1000 ? EUR_ROUND : EUR).format(n)

/** Precio de una carta para mostrar: «desde» si es solo el anuncio más barato. */
export const priceLabel = (p: CardPrice) => `${p.is_low ? 'desde ' : ''}${formatEur(p.eur)}`

export const PRICE_LOW_HINT = 'Sin ventas recientes en Cardmarket: es el precio del anuncio más barato.'
