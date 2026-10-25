// Menú superior común a todas las páginas.
import type { Page } from '../lib/routes'

export type { Page }

export default function SiteNav({ active }: { active: Page }) {
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
      <a href="/scan" className={`nav-scan ${active === 'scan' ? 'active' : ''}`}>
        Escáner
      </a>
    </nav>
  )
}
