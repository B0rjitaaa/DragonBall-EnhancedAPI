// Menú superior común a todas las páginas.
import { useEffect, useState } from 'react'
import { api } from '../lib/api'
import { newsSeenAt } from '../lib/news'
import type { Page } from '../lib/routes'

export type { Page }

export default function SiteNav({ active }: { active: Page }) {
  // Novedades desde tu última visita a esa página (aviso discreto junto al enlace).
  const [unseen, setUnseen] = useState(0)
  useEffect(() => {
    if (active === 'news') return
    api
      .changesCount(newsSeenAt())
      .then((r) => setUnseen(r.count))
      .catch(() => {})
  }, [active])

  return (
    <nav className="site-nav" aria-label="Secciones">
      <a href="/" className={active === 'search' ? 'active' : ''}>
        Buscador
      </a>
      <a href="/collection" className={active === 'collection' ? 'active' : ''}>
        Mi colección
      </a>
      <a href="/locations" className={active === 'locations' ? 'active' : ''}>
        Ubicaciones
      </a>
      <a href="/news" className={active === 'news' ? 'active' : ''}>
        Novedades
        {unseen > 0 && active !== 'news' && (
          <span className="nav-badge" title={`${unseen} novedades desde tu última visita`}>
            {unseen > 99 ? '99+' : unseen}
          </span>
        )}
      </a>
      <a href="/scan" className={`nav-scan ${active === 'scan' ? 'active' : ''}`}>
        Escáner
      </a>
    </nav>
  )
}
