/** Ruta de la web que no existe (p. ej. un enlace antiguo o mal copiado). */
export default function NotFoundPage() {
  return (
    <main className="notfound-page">
      <div className="ball notfound-ball" aria-hidden>
        ★
      </div>
      <p className="notfound-code">ERROR 404</p>
      <h1>Page not found</h1>
      <p className="muted">
        The address <code>{window.location.pathname}</code> doesn't exist on this site.
      </p>
      <div className="notfound-links">
        <a className="btn primary" href="/">
          Go to search
        </a>
        <a className="btn" href="/collection">
          My collection
        </a>
      </div>
    </main>
  )
}
