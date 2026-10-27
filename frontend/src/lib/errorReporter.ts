/** Avisa al servidor de los errores de JavaScript (se ven en /admin → Errores). */

const BASE = import.meta.env.VITE_API_URL ?? '/api'
// Ruido que no es de la web: extensiones del navegador y avisos inofensivos.
const IGNORE = [/ResizeObserver loop/, /^Script error\.?$/, /extension:\/\//]
const MAX_PER_PAGE = 10

const sent = new Set<string>()

function report(kind: string, message: string, stack = '') {
  const where = stack.split('\n').find((l) => /\.(js|tsx?)(\?|:)/.test(l))?.trim().slice(0, 300) ?? ''
  const key = `${kind}|${message}|${where}`
  if (!message || IGNORE.some((re) => re.test(message) || re.test(stack)) || sent.has(key) || sent.size >= MAX_PER_PAGE) return
  sent.add(key)
  // Sin `where` el servidor agrupa por el mensaje. Se quitan las versiones (?v=…) para que agrupe.
  const body = { kind, message: message.slice(0, 2000), where: where.replace(/\?[^:)]*/, ''), stack: stack.slice(0, 10000), page: location.pathname + location.search }
  fetch(`${BASE}/errors/`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body), keepalive: true }).catch(() => {})
}

function fromReason(reason: unknown) {
  if (reason instanceof Error) report(reason.name, reason.message, reason.stack)
  else report('UnhandledRejection', String(reason))
}

export function installErrorReporter() {
  if (import.meta.env.DEV) return
  window.addEventListener('error', (e) => {
    if (e.error instanceof Error) report(e.error.name, e.error.message, e.error.stack)
    else if (e.message) report('Error', e.message, e.filename ? `${e.filename}:${e.lineno}:${e.colno}` : '')
  })
  window.addEventListener('unhandledrejection', (e) => fromReason(e.reason))
}
