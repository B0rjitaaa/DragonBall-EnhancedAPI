// Menú superior común a todas las páginas: Buscador y Mi colección, más el
// acceso al escáner (DragonBall-CameraCardChecker, mismo servidor, puerto 80).

export type Page = 'search' | 'collection'

const SCANNER_URL = `http://${window.location.hostname}/`

export default function SiteNav({ active }: { active: Page }) {
  return (
    <nav className="site-nav" aria-label="Secciones">
      <a href="/" className={active === 'search' ? 'active' : ''}>
        Buscador
      </a>
      <a href="/coleccion" className={active === 'collection' ? 'active' : ''}>
        Mi colección
      </a>
      <a href={SCANNER_URL} className="external" title="Escáner de cartas (DragonBall-CameraCardChecker)">
        Escáner ↗
      </a>
    </nav>
  )
}
