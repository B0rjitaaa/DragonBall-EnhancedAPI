// Texto de carta tal como llega de Bandai: saltos de línea en <br>, a veces «&lt;Pan&gt;» escapado y
// a veces «<Pan>» sin escapar (no es HTML: es el nombre de una carta), así que solo se quitan etiquetas HTML reales.
const HTML_TAG = /<\/?(?:b|i|u|em|strong|span|font|p|div|small|sup|sub)\b[^>]*>/gi
const ENTITIES: Record<string, string> = { lt: '<', gt: '>', amp: '&', quot: '"', apos: "'", nbsp: ' ' }

/** «&lt;Pan&gt;» → «<Pan>» (y &amp;, &quot;, &#39;, &#x27;…). */
export function decodeEntities(text: string): string {
  return text.replace(/&(#x[0-9a-f]+|#\d+|[a-z]+);/gi, (whole, name: string) => {
    if (name[0] === '#') {
      const code = name[1].toLowerCase() === 'x' ? parseInt(name.slice(2), 16) : parseInt(name.slice(1), 10)
      return Number.isFinite(code) ? String.fromCodePoint(code) : whole
    }
    return ENTITIES[name.toLowerCase()] ?? whole
  })
}

/** Texto plano de una carta: líneas separadas por \n, sin etiquetas HTML y con «<» y «>» de verdad. */
export function plainCardText(text: string): string {
  return decodeEntities(text.replace(/<br\s*\/?>/gi, '\n').replace(HTML_TAG, ''))
}
