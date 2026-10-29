// Franja de aviso cuando algo crítico del sistema está caído (según /api/health/).
// Los avisos menores (sync atrasado, copia vieja…) no salen aquí: solo en /api/health/.
import { useEffect, useState } from 'react'

const HEALTH_URL = `${import.meta.env.VITE_API_URL ?? '/api'}/health/`
const RECHECK_MS = 60_000
const DISMISS_KEY = 'dbs-health-dismissed'

/** Qué deja de funcionar cuando cae cada pieza crítica. */
const MESSAGES: Record<string, string> = {
  database: "The database isn't responding: search and My collection don't work right now.",
  redis: "Redis isn't responding: the scanner and background tasks are stopped.",
  scanner_worker: "The scanner isn't available right now.",
  worker: 'Background tasks (Bandai sync, imports) are stopped.',
}
const SERVER_DOWN = "The server isn't responding right now."

interface Check {
  key: string
  kind: string
  ok: boolean | null
}

/** Mensajes de lo crítico que está caído; [] si todo va bien. */
async function fetchProblems(): Promise<string[]> {
  let body: { checks?: Check[] }
  try {
    const res = await fetch(HEALTH_URL)
    body = await res.json() // 200 y 503 traen el mismo JSON
  } catch {
    return [SERVER_DOWN]
  }
  if (!body.checks) return [SERVER_DOWN] // 503 de nginx: el backend no contesta
  const down = body.checks.filter((c) => c.kind === 'critical' && !c.ok).map((c) => c.key)
  // Si no hay base de datos ni Redis, lo demás es consecuencia: basta con decir eso.
  const root = down.filter((k) => k === 'database' || k === 'redis')
  return (root.length ? root : down).map((k) => MESSAGES[k] ?? `${k} isn't responding.`)
}

function readDismissed(): string | null {
  try {
    return sessionStorage.getItem(DISMISS_KEY)
  } catch {
    return null
  }
}

export default function HealthBanner() {
  const [problems, setProblems] = useState<string[]>([])
  const [dismissed, setDismissed] = useState(readDismissed)

  useEffect(() => {
    let alive = true
    const check = () => {
      if (document.visibilityState !== 'visible') return
      fetchProblems().then((p) => alive && setProblems(p))
    }
    check()
    const timer = window.setInterval(check, RECHECK_MS)
    document.addEventListener('visibilitychange', check)
    return () => {
      alive = false
      window.clearInterval(timer)
      document.removeEventListener('visibilitychange', check)
    }
  }, [])

  // Cerrar el aviso lo oculta en esta pestaña hasta que cambie lo que está caído.
  const signature = problems.join('|')
  if (!problems.length || dismissed === signature) return null

  const dismiss = () => {
    setDismissed(signature)
    try {
      sessionStorage.setItem(DISMISS_KEY, signature)
    } catch {
      /* sin almacenamiento: se cierra solo hasta recargar */
    }
  }

  return (
    <div className="health-banner" role="status">
      <span aria-hidden="true">⚠</span>
      <div className="health-banner-text">
        {problems.map((p) => (
          <p key={p}>{p}</p>
        ))}
      </div>
      <button type="button" onClick={dismiss} aria-label="Dismiss notice" title="Dismiss notice">
        ×
      </button>
    </div>
  )
}
