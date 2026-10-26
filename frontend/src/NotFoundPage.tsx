/** Ruta de la web que no existe (p. ej. un enlace antiguo o mal copiado). */
export default function NotFoundPage() {
  return (
    <main className="notfound-page">
      <div className="ball notfound-ball" aria-hidden>
        ★
      </div>
      <p className="notfound-code">ERROR 404</p>
      <h1>Página no encontrada</h1>
      <p className="muted">
        La dirección <code>{window.location.pathname}</code> no existe en esta web.
      </p>
      <div className="notfound-links">
        <a className="btn primary" href="/">
          Ir al buscador
        </a>
        <a className="btn" href="/collection">
          Mi colección
        </a>
      </div>
    </main>
  )
}
