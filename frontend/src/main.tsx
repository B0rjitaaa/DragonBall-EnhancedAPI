import { StrictMode, Suspense, lazy } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.tsx'
import LocationsPage from './LocationsPage.tsx'
import NewsPage from './NewsPage.tsx'
import PricesPage from './PricesPage.tsx'
import NotFoundPage from './NotFoundPage.tsx'
import HealthBanner from './components/HealthBanner.tsx'
import SiteNav from './components/SiteNav.tsx'
import { installErrorReporter } from './lib/errorReporter.ts'
import { currentPage, upgradeLegacyUrl } from './lib/routes.ts'

// Dos páginas con el mismo buscador: todo el catálogo (/) y Mi colección
// (/collection, solo tus cartas; /collection/deck/<uid> dentro de un mazo),
// más la de ubicaciones de Mi colección (/locations) y el escáner (/scan).
installErrorReporter()
upgradeLegacyUrl()
// El escáner (cámara, React Query…) solo se descarga al abrir /scan.
const ScanPage = lazy(() => import('./scan/ScanPage.tsx'))
const page = currentPage()

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <SiteNav active={page} />
    <HealthBanner />
    {page === 'locations' ? (
      <LocationsPage />
    ) : page === 'news' ? (
      <NewsPage />
    ) : page === 'prices' ? (
      <PricesPage />
    ) : page === 'notfound' ? (
      <NotFoundPage />
    ) : page === 'scan' ? (
      <Suspense fallback={<p className="muted" style={{ padding: '1rem' }}>Cargando el escáner…</p>}>
        <ScanPage />
      </Suspense>
    ) : (
      <App scope={page === 'collection' ? 'collection' : 'all'} />
    )}
  </StrictMode>,
)
