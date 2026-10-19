import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.tsx'
import SiteNav from './components/SiteNav.tsx'
import MyCollection from './MyCollection.tsx'

// Dos páginas: el buscador (/) y Mi colección (/coleccion). El buscador guarda
// su estado en el # de la URL, así que la colección va por ruta.
const isCollection = window.location.pathname.replace(/\/+$/, '') === '/coleccion'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <SiteNav active={isCollection ? 'collection' : 'search'} />
    {isCollection ? <MyCollection /> : <App />}
  </StrictMode>,
)
