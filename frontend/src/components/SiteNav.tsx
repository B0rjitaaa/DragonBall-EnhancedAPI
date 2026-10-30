// Menú común a todas las páginas: arriba en el ordenador; en el móvil, barra de pestañas abajo
// (Search, Collection, Locations, Scanner y «More» con Prices, News y Wiki).
import { useEffect, useState } from 'react'
import { api } from '../lib/api'
import { newsSeenAt } from '../lib/news'
import type { Page } from '../lib/routes'

export type { Page }

// Las de «More» en el móvil.
const MORE: Page[] = ['prices', 'news', 'wiki']

export default function SiteNav({ active }: { active: Page }) {
  // Novedades desde tu última visita a esa página (aviso discreto junto al enlace).
  const [unseen, setUnseen] = useState(0)
  const [moreOpen, setMoreOpen] = useState(false)
  useEffect(() => {
    if (active === 'news') return
    api
      .changesCount(newsSeenAt())
      .then((r) => setUnseen(r.count))
      .catch(() => {})
  }, [active])
  useEffect(() => {
    if (!moreOpen) return
    const onKey = (e: KeyboardEvent) => e.key === 'Escape' && setMoreOpen(false)
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [moreOpen])

  const badge = unseen > 0 && active !== 'news' && (
    <span className="nav-badge" title={`${unseen} updates since your last visit`}>
      {unseen > 99 ? '99+' : unseen}
    </span>
  )
  const link = (page: Page, href: string, label: string, icon: string, extra = '', short = label) => (
    <a
      href={href}
      className={`nav-${page} ${extra} ${active === page ? 'active' : ''}`}
      aria-current={active === page ? 'page' : undefined}
    >
      <span className="nav-icon" aria-hidden>
        {icon}
      </span>
      <span className="nav-label">{label}</span>
      <span className="nav-label-short">{short}</span>
      {page === 'news' && badge}
    </a>
  )

  return (
    <>
      <nav className="site-nav" aria-label="Sections">
        {link('search', '/', 'Search', '🔎')}
        {link('collection', '/collection', 'My collection', '🗂️', '', 'Collection')}
        {link('locations', '/locations', 'Locations', '📦')}
        {link('prices', '/prices', 'Prices', '💶', 'nav-more-item')}
        {link('news', '/news', 'News', '🆕', 'nav-more-item')}
        {link('wiki', '/wiki', 'Wiki', '📖', 'nav-more-item')}
        {link('scan', '/scan', 'Scanner', '📷')}
        <button
          type="button"
          className={`nav-more ${MORE.includes(active) || moreOpen ? 'active' : ''}`}
          onClick={() => setMoreOpen((v) => !v)}
          aria-expanded={moreOpen}
          aria-haspopup="menu"
        >
          <span className="nav-icon" aria-hidden>
            ⋯
          </span>
          <span className="nav-label-short">More</span>
          {badge}
        </button>
      </nav>
      {moreOpen && (
        <>
          <div className="nav-more-backdrop" onClick={() => setMoreOpen(false)} aria-hidden />
          <div className="nav-more-sheet" role="menu">
            {link('prices', '/prices', 'Prices', '💶')}
            {link('news', '/news', 'News', '🆕')}
            {link('wiki', '/wiki', 'Wiki', '📖')}
          </div>
        </>
      )}
    </>
  )
}
