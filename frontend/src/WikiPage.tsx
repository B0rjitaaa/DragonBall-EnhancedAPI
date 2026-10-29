// Wiki (/wiki y /wiki/<slug>): guía de uso y documentación técnica, en inglés y en español (botón
// ES / EN). El contenido es el Markdown de frontend/wiki/<idioma>/ (ver lib/wiki.ts), el mismo que se
// lee en el repositorio. Va en tema claro de lectura, aparte del oscuro del resto de la web.
import { useEffect, useMemo, useState, type MouseEvent } from 'react'
import {
  WIKI_ARTICLES, WIKI_CATEGORIES, WIKI_LANGS, articleBySlug, articleText, imageUrl, initialLang, renderArticle, saveLang,
  wikiPath, type WikiArticle, type WikiLang,
} from './lib/wiki'
import NotFoundPage from './NotFoundPage'

const REPO_WIKI = 'https://github.com/B0rjitaaa/DragonBall-EnhancedAPI/tree/main/frontend/wiki'

// Los textos propios de la página (los artículos ya vienen en su idioma).
const TEXT = {
  en: {
    articles: (n: number) => `${n} articles`,
    heading: 'How can we help?',
    intro: 'How each part of the app works, where the data comes from and how everything is built inside.',
    placeholder: 'Search a topic: “fakes”, “burst”, “Cardmarket”, “backup”…',
    searchLabel: 'Search the wiki',
    categories: 'Categories',
    results: (n: number, q: string) => `${n} ${n === 1 ? 'article' : 'articles'} about “${q}”`,
    empty: 'Nothing about that. Try another word or browse the categories.',
    read: 'Read →',
    all: 'All articles',
    home: '← Wiki home',
    youAreIn: 'You are in',
    minutes: (n: number) => `${n} min read`,
    repo: 'View on GitHub ↗',
    more: 'More articles',
    prev: '← Previous',
    next: 'Next →',
    onThisPage: 'On this page',
    top: 'Back to top',
    zoom: 'Enlarged image',
    close: 'Click anywhere or press Esc to close',
    language: 'Language',
  },
  es: {
    articles: (n: number) => `${n} artículos`,
    heading: '¿En qué te podemos ayudar?',
    intro: 'Cómo se usa cada parte de la web, de dónde salen los datos y cómo está montado todo por dentro.',
    placeholder: 'Busca un tema: «fakes», «burst», «Cardmarket», «backup»…',
    searchLabel: 'Buscar en la wiki',
    categories: 'Categorías',
    results: (n: number, q: string) => `${n} ${n === 1 ? 'artículo' : 'artículos'} sobre «${q}»`,
    empty: 'No hay nada sobre eso. Prueba con otra palabra o mira las categorías.',
    read: 'Leer →',
    all: 'Todos los artículos',
    home: '← Portada de la wiki',
    youAreIn: 'Estás en',
    minutes: (n: number) => `${n} min de lectura`,
    repo: 'Ver en GitHub ↗',
    more: 'Más artículos',
    prev: '← Anterior',
    next: 'Siguiente →',
    onThisPage: 'En esta página',
    top: 'Volver arriba',
    zoom: 'Imagen ampliada',
    close: 'Pulsa en cualquier sitio o Esc para cerrar',
    language: 'Idioma',
  },
} satisfies Record<WikiLang, unknown>

function norm(text: string): string {
  return text.toLowerCase().normalize('NFD').replace(/[̀-ͯ]/g, '')
}

function wikiSlug(): string | null {
  const m = window.location.pathname.match(/^\/wiki\/([a-z0-9-]+)\/?$/)
  return m ? m[1] : null
}

/** Artículos que contienen todas las palabras: primero los que las tienen en el título. */
function searchArticles(query: string, lang: WikiLang): WikiArticle[] | null {
  const words = norm(query).split(/\s+/).filter(Boolean)
  if (!words.length) return null
  return WIKI_ARTICLES.map((a) => {
    const head = norm(`${a.title[lang]} ${a.excerpt[lang]} ${a.keywords ?? ''}`)
    const body = norm(articleText(a.slug, lang))
    if (!words.every((w) => head.includes(w) || body.includes(w))) return null
    return { a, score: words.filter((w) => head.includes(w)).length }
  })
    .filter((r): r is { a: WikiArticle; score: number } => r != null)
    .sort((x, y) => y.score - x.score)
    .map((r) => r.a)
}

/** Botón ES / EN: cambia el idioma de toda la wiki y lo recuerda. */
function LangSwitch({ lang, onChange }: { lang: WikiLang; onChange: (lang: WikiLang) => void }) {
  return (
    <div className="wiki-lang" role="group" aria-label={TEXT[lang].language}>
      {WIKI_LANGS.map((l) => (
        <button key={l} type="button" className={l === lang ? 'active' : ''} aria-pressed={l === lang} lang={l} onClick={() => onChange(l)}>
          {l.toUpperCase()}
        </button>
      ))}
    </div>
  )
}

export default function WikiPage() {
  const slug = wikiSlug()
  const article = slug ? articleBySlug(slug) : undefined
  const [lang, setLang] = useState<WikiLang>(initialLang)
  const changeLang = (l: WikiLang) => {
    setLang(l)
    saveLang(l)
  }
  useEffect(() => {
    document.title = article ? `${article.title[lang]} · Wiki` : 'Wiki · DragonBall EnhancedAPI'
    document.documentElement.lang = lang
    return () => {
      document.documentElement.lang = 'en'
    }
  }, [article, lang])
  if (slug && !article) return <NotFoundPage />
  return (
    <div className="wiki-shell" lang={lang}>
      <LangSwitch lang={lang} onChange={changeLang} />
      {article ? <WikiArticleView key={`${article.slug}-${lang}`} article={article} lang={lang} /> : <WikiIndex lang={lang} />}
    </div>
  )
}

function ArticleCard({ a, lang }: { a: WikiArticle; lang: WikiLang }) {
  const cover = a.cover ? imageUrl(a.cover) : undefined
  return (
    <a className="wiki-card" href={wikiPath(a.slug)}>
      <div className={`wiki-card-cover ${cover ? '' : 'empty'}`}>
        {cover ? <img src={cover} alt="" loading="lazy" /> : <span aria-hidden>{a.icon}</span>}
      </div>
      <div className="wiki-card-body">
        <h3>{a.title[lang]}</h3>
        <p>{a.excerpt[lang]}</p>
        <span className="wiki-card-more">{TEXT[lang].read}</span>
      </div>
    </a>
  )
}

function WikiIndex({ lang }: { lang: WikiLang }) {
  const t = TEXT[lang]
  const [query, setQuery] = useState('')
  const results = useMemo(() => searchArticles(query, lang), [query, lang])

  return (
    <div className="wiki-index">
      <header className="wiki-hero">
        <p className="wiki-eyebrow">📖 Wiki · {t.articles(WIKI_ARTICLES.length)}</p>
        <h1>{t.heading}</h1>
        <p className="wiki-hero-text">{t.intro}</p>
        <div className="wiki-search">
          <span aria-hidden>🔍</span>
          <input
            type="search"
            placeholder={t.placeholder}
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            aria-label={t.searchLabel}
            autoFocus
          />
        </div>
        {!results && (
          <nav className="wiki-chips" aria-label={t.categories}>
            {WIKI_CATEGORIES.map((c) => (
              <a key={c.id} href={`#${c.id}`}>
                <span aria-hidden>{c.icon}</span> {c.label[lang]}
              </a>
            ))}
          </nav>
        )}
      </header>

      {results ? (
        <section className="wiki-category">
          <h2 className="wiki-results-head">
            {t.results(results.length, query.trim())}
          </h2>
          {results.length ? (
            <div className="wiki-grid">
              {results.map((a) => (
                <ArticleCard key={a.slug} a={a} lang={lang} />
              ))}
            </div>
          ) : (
            <p className="wiki-empty">{t.empty}</p>
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
                  <h2>{cat.label[lang]}</h2>
                  <p>{cat.blurb[lang]}</p>
                </div>
              </div>
              <div className="wiki-grid">
                {articles.map((a) => (
                  <ArticleCard key={a.slug} a={a} lang={lang} />
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
function WikiSidebar({ current, lang }: { current: WikiArticle; lang: WikiLang }) {
  return (
    <details className="wiki-sidebar" open={window.innerWidth > 1000}>
      <summary>{TEXT[lang].all}</summary>
      <a className="wiki-sidebar-home" href={wikiPath()}>
        {TEXT[lang].home}
      </a>
      {WIKI_CATEGORIES.map((cat) => (
        <div key={cat.id} className="wiki-sidebar-group">
          <strong>
            <span aria-hidden>{cat.icon}</span> {cat.label[lang]}
          </strong>
          {WIKI_ARTICLES.filter((a) => a.category === cat.id).map((a) => (
            <a
              key={a.slug}
              href={wikiPath(a.slug)}
              className={a.slug === current.slug ? 'active' : ''}
              aria-current={a.slug === current.slug ? 'page' : undefined}
            >
              {a.title[lang]}
            </a>
          ))}
        </div>
      ))}
    </details>
  )
}

function WikiArticleView({ article, lang }: { article: WikiArticle; lang: WikiLang }) {
  const t = TEXT[lang]
  const rendered = useMemo(() => renderArticle(article.slug, lang), [article.slug, lang])
  const [zoom, setZoom] = useState<{ src: string; alt: string } | null>(null)
  const [activeId, setActiveId] = useState<string | null>(null)
  const [showTop, setShowTop] = useState(false)
  const category = WIKI_CATEGORIES.find((c) => c.id === article.category)
  const index = WIKI_ARTICLES.indexOf(article)
  const prev = WIKI_ARTICLES[index - 1]
  const next = WIKI_ARTICLES[index + 1]
  const minutes = Math.max(1, Math.round(articleText(article.slug, lang).split(/\s+/).length / 200))

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
      <WikiSidebar current={article} lang={lang} />

      <article className="wiki-article">
        <nav className="wiki-breadcrumb" aria-label={t.youAreIn}>
          <a href={wikiPath()}>Wiki</a>
          <span aria-hidden>›</span>
          <a href={`${wikiPath()}#${category?.id ?? ''}`}>{category?.label[lang]}</a>
        </nav>
        <h1>
          <span className="wiki-title-icon" aria-hidden>
            {article.icon}
          </span>
          {article.title[lang]}
        </h1>
        <p className="wiki-excerpt">{article.excerpt[lang]}</p>
        <p className="wiki-meta">
          {t.minutes(minutes)} ·{' '}
          <a href={`${REPO_WIKI}/${lang}/${article.slug}.md`} target="_blank" rel="noreferrer">
            {t.repo}
          </a>
        </p>
        {rendered && (
          <div className="wiki-body" onClick={onBodyClick} dangerouslySetInnerHTML={{ __html: rendered.html }} />
        )}
        <nav className="wiki-pager" aria-label={t.more}>
          {prev ? (
            <a href={wikiPath(prev.slug)}>
              <small>{t.prev}</small>
              <strong>{prev.title[lang]}</strong>
            </a>
          ) : (
            <span />
          )}
          {next && (
            <a href={wikiPath(next.slug)} className="next">
              <small>{t.next}</small>
              <strong>{next.title[lang]}</strong>
            </a>
          )}
        </nav>
      </article>

      {rendered && rendered.toc.length > 1 && (
        <aside className="wiki-toc" aria-label={t.onThisPage}>
          <strong>{t.onThisPage}</strong>
          {rendered.toc.map((h) => (
            <a key={h.id} href={`#${h.id}`} className={h.id === activeId ? 'active' : ''}>
              {h.text}
            </a>
          ))}
        </aside>
      )}

      {showTop && (
        <button className="wiki-top" onClick={() => window.scrollTo({ top: 0, behavior: 'smooth' })} aria-label={t.top}>
          ↑
        </button>
      )}
      {zoom && (
        <div className="wiki-zoom" onClick={() => setZoom(null)} role="dialog" aria-label={zoom.alt || t.zoom}>
          <img src={zoom.src} alt={zoom.alt} />
          {zoom.alt && <p>{zoom.alt}</p>}
          <small>{t.close}</small>
        </div>
      )}
    </div>
  )
}
