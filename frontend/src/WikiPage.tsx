// Wiki (/wiki y /wiki/<slug>): guía de uso y documentación técnica. El contenido es el Markdown de
// frontend/wiki/ (ver lib/wiki.ts), el mismo que se lee en el repositorio. Va en tema claro de lectura,
// aparte del oscuro del resto de la web.
import { useEffect, useMemo, useState, type MouseEvent } from 'react'
import {
  WIKI_ARTICLES, WIKI_CATEGORIES, articleBySlug, articleText, imageUrl, renderArticle, wikiPath, type WikiArticle,
} from './lib/wiki'
import NotFoundPage from './NotFoundPage'

const REPO_WIKI = 'https://github.com/B0rjitaaa/DragonBall-EnhancedAPI/tree/main/frontend/wiki'

function norm(text: string): string {
  return text.toLowerCase().normalize('NFD').replace(/[̀-ͯ]/g, '')
}

function wikiSlug(): string | null {
  const m = window.location.pathname.match(/^\/wiki\/([a-z0-9-]+)\/?$/)
  return m ? m[1] : null
}

/** Artículos que contienen todas las palabras: primero los que las tienen en el título. */
function searchArticles(query: string): WikiArticle[] | null {
  const words = norm(query).split(/\s+/).filter(Boolean)
  if (!words.length) return null
  return WIKI_ARTICLES.map((a) => {
    const head = norm(`${a.title} ${a.excerpt} ${a.keywords ?? ''}`)
    const body = norm(articleText(a.slug))
    if (!words.every((w) => head.includes(w) || body.includes(w))) return null
    return { a, score: words.filter((w) => head.includes(w)).length }
  })
    .filter((r): r is { a: WikiArticle; score: number } => r != null)
    .sort((x, y) => y.score - x.score)
    .map((r) => r.a)
}

export default function WikiPage() {
  const slug = wikiSlug()
  const article = slug ? articleBySlug(slug) : undefined
  useEffect(() => {
    document.title = article ? `${article.title} · Wiki` : 'Wiki · DragonBall EnhancedAPI'
  }, [article])
  if (slug && !article) return <NotFoundPage />
  return <div className="wiki-shell">{article ? <WikiArticleView article={article} /> : <WikiIndex />}</div>
}

function ArticleCard({ a }: { a: WikiArticle }) {
  const cover = a.cover ? imageUrl(a.cover) : undefined
  return (
    <a className="wiki-card" href={wikiPath(a.slug)}>
      <div className={`wiki-card-cover ${cover ? '' : 'empty'}`}>
        {cover ? <img src={cover} alt="" loading="lazy" /> : <span aria-hidden>{a.icon}</span>}
      </div>
      <div className="wiki-card-body">
        <h3>{a.title}</h3>
        <p>{a.excerpt}</p>
        <span className="wiki-card-more">Leer →</span>
      </div>
    </a>
  )
}

function WikiIndex() {
  const [query, setQuery] = useState('')
  const results = useMemo(() => searchArticles(query), [query])

  return (
    <div className="wiki-index">
      <header className="wiki-hero">
        <p className="wiki-eyebrow">📖 Wiki · {WIKI_ARTICLES.length} artículos</p>
        <h1>¿En qué te podemos ayudar?</h1>
        <p className="wiki-hero-text">
          Cómo se usa cada parte de la web, de dónde salen los datos y cómo está montado todo por dentro.
        </p>
        <div className="wiki-search">
          <span aria-hidden>🔍</span>
          <input
            type="search"
            placeholder="Busca un tema: «falsas», «ráfaga», «Cardmarket», «copia de seguridad»…"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            aria-label="Buscar en la wiki"
            autoFocus
          />
        </div>
        {!results && (
          <nav className="wiki-chips" aria-label="Categorías">
            {WIKI_CATEGORIES.map((c) => (
              <a key={c.id} href={`#${c.id}`}>
                <span aria-hidden>{c.icon}</span> {c.label}
              </a>
            ))}
          </nav>
        )}
      </header>

      {results ? (
        <section className="wiki-category">
          <h2 className="wiki-results-head">
            {results.length} {results.length === 1 ? 'artículo' : 'artículos'} sobre «{query.trim()}»
          </h2>
          {results.length ? (
            <div className="wiki-grid">
              {results.map((a) => (
                <ArticleCard key={a.slug} a={a} />
              ))}
            </div>
          ) : (
            <p className="wiki-empty">No hay nada sobre eso. Prueba con otra palabra o mira las categorías.</p>
          )}
        </section>
      ) : (
        WIKI_CATEGORIES.map((cat) => {
          const articles = WIKI_ARTICLES.filter((a) => a.category === cat.id)
          if (!articles.length) return null
          return (
            <section key={cat.id} id={cat.id} className="wiki-category">
              <div className="wiki-category-head">
                <span className="wiki-category-icon" aria-hidden>
                  {cat.icon}
                </span>
                <div>
                  <h2>{cat.label}</h2>
                  <p>{cat.blurb}</p>
                </div>
              </div>
              <div className="wiki-grid">
                {articles.map((a) => (
                  <ArticleCard key={a.slug} a={a} />
                ))}
              </div>
            </section>
          )
        })
      )}
    </div>
  )
}

/** Menú lateral con todos los artículos (en el móvil, plegable). */
function WikiSidebar({ current }: { current: WikiArticle }) {
  return (
    <details className="wiki-sidebar" open={window.innerWidth > 1000}>
      <summary>Todos los artículos</summary>
      <a className="wiki-sidebar-home" href={wikiPath()}>
        ← Portada de la wiki
      </a>
      {WIKI_CATEGORIES.map((cat) => (
        <div key={cat.id} className="wiki-sidebar-group">
          <strong>
            <span aria-hidden>{cat.icon}</span> {cat.label}
          </strong>
          {WIKI_ARTICLES.filter((a) => a.category === cat.id).map((a) => (
            <a
              key={a.slug}
              href={wikiPath(a.slug)}
              className={a.slug === current.slug ? 'active' : ''}
              aria-current={a.slug === current.slug ? 'page' : undefined}
            >
              {a.title}
            </a>
          ))}
        </div>
      ))}
    </details>
  )
}

function WikiArticleView({ article }: { article: WikiArticle }) {
  const rendered = useMemo(() => renderArticle(article.slug), [article.slug])
  const [zoom, setZoom] = useState<{ src: string; alt: string } | null>(null)
  const [activeId, setActiveId] = useState<string | null>(null)
  const [showTop, setShowTop] = useState(false)
  const category = WIKI_CATEGORIES.find((c) => c.id === article.category)
  const index = WIKI_ARTICLES.indexOf(article)
  const prev = WIKI_ARTICLES[index - 1]
  const next = WIKI_ARTICLES[index + 1]
  const minutes = Math.max(1, Math.round(articleText(article.slug).split(/\s+/).length / 200))

  // Al entrar con #apartado, la página aún no estaba pintada: se baja ahora.
  useEffect(() => {
    const id = decodeURIComponent(window.location.hash.slice(1))
    if (id) document.getElementById(id)?.scrollIntoView()
  }, [])

  // Apartado que se está leyendo (se resalta en «En esta página») y botón de volver arriba.
  useEffect(() => {
    const ids = rendered?.toc.map((h) => h.id) ?? []
    const onScroll = () => {
      setShowTop(window.scrollY > 900)
      let current: string | null = null
      for (const id of ids) {
        const el = document.getElementById(id)
        if (el && el.getBoundingClientRect().top < 140) current = id
      }
      setActiveId(current)
    }
    onScroll()
    window.addEventListener('scroll', onScroll, { passive: true })
    return () => window.removeEventListener('scroll', onScroll)
  }, [rendered])

  useEffect(() => {
    if (!zoom) return
    const onKey = (e: KeyboardEvent) => e.key === 'Escape' && setZoom(null)
    document.addEventListener('keydown', onKey)
    return () => document.removeEventListener('keydown', onKey)
  }, [zoom])

  const onBodyClick = (e: MouseEvent<HTMLElement>) => {
    const target = e.target as HTMLElement
    if (target.tagName === 'IMG') {
      const img = target as HTMLImageElement
      setZoom({ src: img.src, alt: img.alt })
    }
  }

  return (
    <div className="wiki-article-layout">
      <WikiSidebar current={article} />

      <article className="wiki-article">
        <nav className="wiki-breadcrumb" aria-label="Estás en">
          <a href={wikiPath()}>Wiki</a>
          <span aria-hidden>›</span>
          <a href={`${wikiPath()}#${category?.id ?? ''}`}>{category?.label}</a>
        </nav>
        <h1>
          <span className="wiki-title-icon" aria-hidden>
            {article.icon}
          </span>
          {article.title}
        </h1>
        <p className="wiki-excerpt">{article.excerpt}</p>
        <p className="wiki-meta">
          {minutes} min de lectura ·{' '}
          <a href={`${REPO_WIKI}/${article.slug}.md`} target="_blank" rel="noreferrer">
            Ver en el repositorio ↗
          </a>
        </p>
        {rendered && (
          <div className="wiki-body" onClick={onBodyClick} dangerouslySetInnerHTML={{ __html: rendered.html }} />
        )}
        <nav className="wiki-pager" aria-label="Más artículos">
          {prev ? (
            <a href={wikiPath(prev.slug)}>
              <small>← Anterior</small>
              <strong>{prev.title}</strong>
            </a>
          ) : (
            <span />
          )}
          {next && (
            <a href={wikiPath(next.slug)} className="next">
              <small>Siguiente →</small>
              <strong>{next.title}</strong>
            </a>
          )}
        </nav>
      </article>

      {rendered && rendered.toc.length > 1 && (
        <aside className="wiki-toc" aria-label="En esta página">
          <strong>En esta página</strong>
          {rendered.toc.map((h) => (
            <a key={h.id} href={`#${h.id}`} className={h.id === activeId ? 'active' : ''}>
              {h.text}
            </a>
          ))}
        </aside>
      )}

      {showTop && (
        <button className="wiki-top" onClick={() => window.scrollTo({ top: 0, behavior: 'smooth' })} aria-label="Volver arriba">
          ↑
        </button>
      )}
      {zoom && (
        <div className="wiki-zoom" onClick={() => setZoom(null)} role="dialog" aria-label={zoom.alt || 'Imagen ampliada'}>
          <img src={zoom.src} alt={zoom.alt} />
          {zoom.alt && <p>{zoom.alt}</p>}
          <small>Pulsa en cualquier sitio o Esc para cerrar</small>
        </div>
      )}
    </div>
  )
}
