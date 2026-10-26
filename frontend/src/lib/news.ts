// Última visita a «Novedades»: se guarda en este navegador para el aviso del menú.
const KEY = 'dbs-news-seen'

export function newsSeenAt(): string | null {
  try {
    return localStorage.getItem(KEY)
  } catch {
    return null
  }
}

export function markNewsSeen(when: string): void {
  try {
    localStorage.setItem(KEY, when)
  } catch {
    // sin almacenamiento (modo privado…): el aviso volverá a salir, nada más
  }
}
