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
    <nav className="site-nav" aria-label="Sections">
      <a href="/" className={active === 'search' ? 'active' : ''}>
        Search
      </a>
      <a href="/collection" className={active === 'collection' ? 'active' : ''}>
        My collection
      </a>
      <a href="/locations" className={active === 'locations' ? 'active' : ''}>
        Locations
      </a>
      <a href="/prices" className={active === 'prices' ? 'active' : ''}>
        Prices
      </a>
      <a href="/news" className={active === 'news' ? 'active' : ''}>
        News
        {unseen > 0 && active !== 'news' && (
          <span className="nav-badge" title={`${unseen} updates since your last visit`}>
            {unseen > 99 ? '99+' : unseen}
          </span>
        )}
      </a>
      <a href="/wiki" className={`nav-wiki ${active === 'wiki' ? 'active' : ''}`} title="User guide and documentation">
        Wiki
      </a>
      <a href="/scan" className={active === 'scan' ? 'active' : ''}>
        Scanner
      </a>
    </nav>
  )
}
