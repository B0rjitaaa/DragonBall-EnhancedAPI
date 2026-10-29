/** Avisa al servidor de los errores de JavaScript y de la API (se ven en /admin → Errores). */

const BASE = import.meta.env.VITE_API_URL ?? '/api'
// Ruido que no es de la web: extensiones del navegador y avisos inofensivos.
const IGNORE = [/ResizeObserver loop/, /^Script error\.?$/, /extension:\/\//]
const MAX_PER_PAGE = 10

const sent = new Set<string>()

/** Token CSRF de Django. Con una sesión iniciada (p. ej. tras entrar en /admin), la API lo exige en
 * POST/PATCH/DELETE; sin sesión no hace falta (la cookie no existe y va vacío). */
export function csrfToken(): string {
  return decodeURIComponent(document.cookie.match(/(?:^|; )csrftoken=([^;]*)/)?.[1] ?? '')
}

function report(kind: string, message: string, stack = '', where?: string) {
  if (import.meta.env.DEV) return
  where ??= stack.split('\n').find((l) => /\.(js|tsx?)(\?|:)/.test(l))?.trim().slice(0, 300) ?? ''
  const key = `${kind}|${message}|${where}`
  if (!message || IGNORE.some((re) => re.test(message) || re.test(stack)) || sent.has(key) || sent.size >= MAX_PER_PAGE) return
  sent.add(key)
  // Sin `where` el servidor agrupa por el mensaje. Se quitan las versiones (?v=…) para que agrupe.
  const body = { kind, message: message.slice(0, 2000), where: where.replace(/\?[^:)]*/, ''), stack: stack.slice(0, 10000), page: location.pathname + location.search }
  fetch(`${BASE}/errors/`, {
    method: 'POST', headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrfToken() }, body: JSON.stringify(body), keepalive: true,
  }).catch(() => {})
}

/** La API ha fallado (5xx) o rechazado la petición (403). Se agrupa por método, ruta (sin ids) y código. */
export function reportApiFailure(method: string, path: string, status: number, detail: string) {
  if (path.startsWith('/errors/')) return
  const route = path.split('?')[0].replace(/\/\d+(?=\/|$)/g, '/:id')
  report('ApiError', `${status} ${method} ${path}: ${detail}`, '', `${status} ${method} ${route}`)
}

function fromReason(reason: unknown) {
  if (reason instanceof Error) report(reason.name, reason.message, reason.stack)
  else report('UnhandledRejection', String(reason))
}

export function installErrorReporter() {
  window.addEventListener('error', (e) => {
    if (e.error instanceof Error) report(e.error.name, e.error.message, e.error.stack)
    else if (e.message) report('Error', e.message, e.filename ? `${e.filename}:${e.lineno}:${e.colno}` : '')
  })
  window.addEventListener('unhandledrejection', (e) => fromReason(e.reason))
}
