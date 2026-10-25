import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.tsx'
import LocationsPage from './LocationsPage.tsx'
import SiteNav from './components/SiteNav.tsx'

// Dos páginas con el mismo buscador: todo el catálogo (/) y Mi colección
// (/coleccion, solo las cartas escaneadas; /coleccion/mazo/<uid> dentro de un mazo),
// más la de ubicaciones de Mi colección (/ubicaciones).
const path = window.location.pathname.replace(/\/+$/, '')
const page = path === '/coleccion' || path.startsWith('/coleccion/') ? 'collection' : path === '/ubicaciones' ? 'locations' : 'search'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <SiteNav active={page} />
    {page === 'locations' ? <LocationsPage /> : <App scope={page === 'collection' ? 'collection' : 'all'} />}
  </StrictMode>,
)
