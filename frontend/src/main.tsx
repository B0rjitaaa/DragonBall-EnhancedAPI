import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.tsx'
import SiteNav from './components/SiteNav.tsx'

// Dos páginas con el mismo buscador: todo el catálogo (/) y Mi colección
// (/coleccion, solo las cartas escaneadas). El estado de filtros va en el #.
const isCollection = window.location.pathname.replace(/\/+$/, '') === '/coleccion'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <SiteNav active={isCollection ? 'collection' : 'search'} />
    <App scope={isCollection ? 'collection' : 'all'} />
  </StrictMode>,
)
