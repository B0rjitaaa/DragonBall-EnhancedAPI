import { marked } from 'marked'

/**
 * Wiki: los artículos son Markdown en frontend/wiki/<idioma>/ (es y en, con los mismos slugs; se
 * leen igual en GitHub) y aquí se pintan en la web (/wiki y /wiki/<slug>). Las capturas viven en
 * frontend/wiki/img/, compartidas por los dos idiomas (se regeneran con scripts/wiki_screenshots.py).
 *
 * En el Markdown los enlaces van entre artículos (`modo-avanzado.md`, `precios.md#fuentes`)
 * y a imágenes (`../img/buscador.jpg`): así funcionan en GitHub, y aquí se cambian por sus
 * rutas en la web. Los avisos usan la sintaxis de GitHub: `> [!TIP]`, `> [!NOTE]`,
 * `> [!WARNING]`, `> [!IMPORTANT]`.
 */

export type WikiLang = 'es' | 'en'
export const WIKI_LANGS: WikiLang[] = ['en', 'es']
/** Un texto en los dos idiomas. */
type T = Record<WikiLang, string>

export interface WikiCategory {
  id: string
  icon: string
  label: T
  blurb: T
}

export interface WikiArticle {
  slug: string
  category: string
  icon: string
  title: T
  excerpt: T
  /** Captura de la tarjeta del índice (en wiki/img/). */
  cover?: string
  /** Palabras extra para el buscador de la wiki (en los dos idiomas). */
  keywords?: string
}

export const WIKI_CATEGORIES: WikiCategory[] = [
  { id: 'empezar', icon: '🚀', label: { en: 'Getting started', es: 'Primeros pasos' }, blurb: { en: 'What the app is, its sections and how to get around.', es: 'Qué es la web, sus secciones y cómo moverte por ella.' } },
  { id: 'instalacion', icon: '🧰', label: { en: 'Installation', es: 'Instalación' }, blurb: { en: 'Installing it with Docker, step by step, and everything that must be running.', es: 'Instalarlo con Docker, paso a paso, y todo lo que debe estar en marcha.' } },
  { id: 'buscador', icon: '🔎', label: { en: 'Search', es: 'Buscador' }, blurb: { en: 'Find any card and understand its details.', es: 'Encontrar cualquier carta y entender su ficha.' } },
  { id: 'coleccion', icon: '🗂️', label: { en: 'Collection & decks', es: 'Colección y mazos' }, blurb: { en: 'Your copies, where they are, and your decks.', es: 'Tus copias, dónde están y tus mazos.' } },
  { id: 'escaner', icon: '📷', label: { en: 'Scanner', es: 'Escáner' }, blurb: { en: 'Adding cards with your phone camera.', es: 'Dar de alta cartas con la cámara del móvil.' } },
  { id: 'precios', icon: '💶', label: { en: 'Prices', es: 'Precios' }, blurb: { en: 'Where each price comes from and what your collection is worth.', es: 'De dónde sale cada precio y el valor de tu colección.' } },
  { id: 'admin', icon: '🛠️', label: { en: 'Administration', es: 'Administración' }, blurb: { en: 'Django admin: price review, errors and backups.', es: 'El admin de Django: revisión de precios, errores y copias.' } },
  { id: 'tecnico', icon: '⚙️', label: { en: 'Technical', es: 'Técnico' }, blurb: { en: 'Architecture, servers, tasks, deployment and API.', es: 'Arquitectura, servidores, tareas, despliegue y API.' } },
  { id: 'ayuda', icon: '💬', label: { en: 'Help', es: 'Ayuda' }, blurb: { en: 'Frequent questions and what to do when something fails.', es: 'Dudas frecuentes y qué hacer cuando algo falla.' } },
]

// El orden de esta lista es el del índice y el de «Anterior / Siguiente».
export const WIKI_ARTICLES: WikiArticle[] = [
  { slug: 'bienvenida', category: 'empezar', icon: '👋', cover: 'buscador.jpg',
    title: { en: 'Welcome to DragonBall EnhancedAPI', es: 'Bienvenido a DragonBall EnhancedAPI' },
    excerpt: { en: 'What this app is, its sections and how it is built at a glance.', es: 'Qué es esta web, qué secciones tiene y cómo está montada a grandes rasgos.' },
    keywords: 'inicio menu secciones navegacion que es home menu sections navigation what is' },
  { slug: 'enlaces-y-navegacion', category: 'empezar', icon: '🔗', cover: 'enlace-carta.jpg',
    title: { en: 'Links, addresses and shortcuts', es: 'Enlaces, direcciones y atajos' },
    excerpt: { en: 'Every search, card and deck has its own address: how to share and save them.', es: 'Cada búsqueda, carta y mazo tiene su propia dirección: cómo compartirlas y guardarlas.' },
    keywords: 'url enlace compartir copiar direccion card favoritos link share copy address bookmark shortcuts keyboard' },

  { slug: 'instalacion', category: 'instalacion', icon: '🧰',
    title: { en: 'Step-by-step installation', es: 'Instalación paso a paso' },
    excerpt: { en: 'On your computer, docker compose up and done; on a home server, with HTTPS, backups and alerts.', es: 'En tu ordenador, docker compose up y listo; en un servidor de casa, con HTTPS, copias y avisos.' },
    keywords: 'instalar instalacion docker compose up env defaults requisitos servidor respaldo admin superuser main fingerprints https systemd backups cron install installation requirements server backup https' },
  { slug: 'servicios', category: 'instalacion', icon: '✅',
    title: { en: 'What must be running', es: 'Qué tiene que estar en marcha' },
    excerpt: { en: 'Containers, tasks, systemd and the backup machine: what each one does and how to check it.', es: 'Contenedores, tareas, systemd y el equipo de respaldo: qué hace cada uno y cómo comprobarlo.' },
    keywords: 'servicios contenedores docker ps celery beat worker systemd timer cron watchdog comprobar estado services containers check status' },

  { slug: 'buscar-cartas', category: 'buscador', icon: '🔎', cover: 'buscador.jpg',
    title: { en: 'Searching cards', es: 'Buscar cartas' },
    excerpt: { en: 'Text search, filter panel, sorting and pagination.', es: 'Búsqueda por texto, panel de filtros, orden y paginación.' },
    keywords: 'buscar texto filtros facetas color energy power orden comillas excluir search text filters facets sort quotes exclude' },
  { slug: 'modo-avanzado', category: 'buscador', icon: '🧩', cover: 'modo-avanzado.jpg',
    title: { en: 'Advanced mode', es: 'Modo avanzado' },
    excerpt: { en: 'Combine conditions with AND / OR / NOT for searches the panel can\'t do.', es: 'Combina condiciones con Y / O / NO para búsquedas que el panel no permite.' },
    keywords: 'avanzado query builder grupos and or not condiciones operadores advanced builder groups conditions operators' },
  { slug: 'ficha-de-carta', category: 'buscador', icon: '🃏', cover: 'ficha-carta.jpg',
    title: { en: 'Card details', es: 'La ficha de una carta' },
    excerpt: { en: 'Everything the detail view shows: text, printings, price, errata, Q&A and your copies.', es: 'Todo lo que muestra el detalle: texto, impresiones, precio, errata, Q&A y tus copias.' },
    keywords: 'detalle modal carta leader awaken impresiones errata q&a ruling banned limited detail printings errata ruling' },
  { slug: 'novedades', category: 'buscador', icon: '🆕', cover: 'novedades.jpg',
    title: { en: 'News', es: 'Novedades' },
    excerpt: { en: 'New cards and catalog changes since your last visit.', es: 'Cartas nuevas y cambios del catálogo desde tu última visita.' },
    keywords: 'novedades cambios nuevas sync bandai news changes new' },

  { slug: 'mi-coleccion', category: 'coleccion', icon: '🗂️', cover: 'coleccion.jpg',
    title: { en: 'My collection', es: 'Mi colección' },
    excerpt: { en: 'Your copies: add, remove, move, mark fakes and see what it is all worth.', es: 'Tus copias: añadir, quitar, mover, marcar falsas y ver cuánto vale todo.' },
    keywords: 'coleccion copias cantidad falsas valor lista cuadricula collection copies quantity fakes value list grid' },
  { slug: 'ubicaciones', category: 'coleccion', icon: '📦', cover: 'ubicaciones.jpg',
    title: { en: 'Locations', es: 'Ubicaciones' },
    excerpt: { en: 'Binders, boxes and decks: where you keep each copy.', es: 'Carpetas, cajas y mazos: dónde guardas cada copia.' },
    keywords: 'ubicaciones carpeta caja binder mover orden locations binder box move order' },
  { slug: 'mazos', category: 'coleccion', icon: '🃏', cover: 'mazo.jpg',
    title: { en: 'Decks', es: 'Mazos' },
    excerpt: { en: 'Leader, Main Deck and Side Deck, list versions, matches, stats and history.', es: 'Leader, Main Deck y Side Deck, versiones de la lista, partidas, estadísticas e histórico.' },
    keywords: 'mazo deck leader side deck partidas estadisticas historico versiones archivar exportar copiar lista simulador deck matches stats history versions archive export copy list time chamber timechamber tcgarena simulator import importar deckplanet topdeckdiffusion enlace link' },
  { slug: 'importar-exportar', category: 'coleccion', icon: '📤', cover: 'csv.jpg',
    title: { en: 'Import, export and collection backup', es: 'Importar, exportar y copia de la colección' },
    excerpt: { en: 'CSV for spreadsheets, and the full JSON backup you can restore.', es: 'CSV para hojas de cálculo, y la copia completa en JSON que se puede restaurar.' },
    keywords: 'csv importar exportar copia backup json excel restaurar sustituir deshacer import export backup spreadsheet restore replace undo' },

  { slug: 'escaner', category: 'escaner', icon: '📷', cover: 'escaner.jpg',
    title: { en: 'Using the scanner', es: 'Usar el escáner' },
    excerpt: { en: 'Scanning from your phone, burst mode and which location cards go to.', es: 'Escanear desde el móvil, modo ráfaga y a qué ubicación van las cartas.' },
    keywords: 'escaner camara movil rafaga https certificado scanner camera phone burst certificate' },
  { slug: 'revisar-escaneos', category: 'escaner', icon: '✅', cover: 'escaner.jpg',
    title: { en: 'Reviewing uncertain scans', es: 'Revisar escaneos dudosos' },
    excerpt: { en: 'What to do when the scanner is not sure about the card or its edition.', es: 'Qué hacer cuando el escáner no está seguro de la carta o de su edición.' },
    keywords: 'revisar dudosos confirmar edicion alt art reconocer review uncertain confirm edition recognize' },
  { slug: 'como-reconoce', category: 'escaner', icon: '🧠',
    title: { en: 'How cards are recognized', es: 'Cómo reconoce las cartas' },
    excerpt: { en: 'Image fingerprints, thresholds and tie-breaks between similar printings.', es: 'Huellas de imagen, umbrales y desempates entre impresiones parecidas.' },
    keywords: 'orb huella reconocimiento umbral impresiones fotos borrado fingerprint recognition threshold printings photos' },

  { slug: 'precios', category: 'precios', icon: '💶', cover: 'precio-ficha.jpg',
    title: { en: 'Where each price comes from', es: 'De dónde sale cada precio' },
    excerpt: { en: 'Cardmarket, TCGplayer and manual prices: the rules, step by step.', es: 'Cardmarket, TCGplayer y precios a mano: las reglas, paso a paso.' },
    keywords: 'precio cardmarket tcgplayer trend ventas anuncio sospechoso manual price sales listing suspect manual' },
  { slug: 'pagina-precios', category: 'precios', icon: '📈', cover: 'precios.jpg',
    title: { en: 'The Prices page', es: 'La página «Prices»' },
    excerpt: { en: 'Collection value, its evolution and the cards rising and falling the most.', es: 'Valor de la colección, su evolución y las cartas que más suben y bajan.' },
    keywords: 'precios valor grafico radar suben bajan caras prices value chart radar rising falling expensive' },
  { slug: 'revisar-precios', category: 'precios', icon: '🧾', cover: 'admin-precios.jpg',
    title: { en: 'Reviewing prices in the admin', es: 'Revisar precios en el admin' },
    excerpt: { en: 'Match cards without a product, fix suspect prices and set prices by hand.', es: 'Emparejar cartas sin producto, corregir dudosos y poner precios a mano.' },
    keywords: 'revision precios admin emparejar dudosos manual falsa impresion price review admin match suspect manual fake printing' },

  { slug: 'admin', category: 'admin', icon: '🛠️', cover: 'admin.jpg',
    title: { en: 'The Django admin', es: 'El admin de Django' },
    excerpt: { en: 'What is in /admin/ and what each section is for.', es: 'Qué hay en /admin/ y para qué sirve cada sección.' },
    keywords: 'admin django usuario login secciones admin user login sections' },
  { slug: 'registro-de-errores', category: 'admin', icon: '🐞', cover: 'admin-errores.jpg',
    title: { en: 'Error log', es: 'Registro de errores' },
    excerpt: { en: 'App and server failures, stored and reported on Telegram.', es: 'Los fallos de la web y del servidor, guardados y avisados por Telegram.' },
    keywords: 'errores log errorlog telegram avisos errors log alerts' },
  { slug: 'copias-de-seguridad', category: 'admin', icon: '💾', cover: 'admin-copias.jpg',
    title: { en: 'Backups', es: 'Copias de seguridad' },
    excerpt: { en: 'Daily backup, on-demand backup from the admin, retention and restore.', es: 'Copia diaria, copia bajo demanda desde el admin, retención y restauración.' },
    keywords: 'backup copia seguridad restaurar pg_dump retencion backup restore retention' },

  { slug: 'arquitectura', category: 'tecnico', icon: '🏗️',
    title: { en: 'Architecture', es: 'Arquitectura' },
    excerpt: { en: 'Services, containers, servers and how they fit together.', es: 'Servicios, contenedores, servidores y cómo encajan.' },
    keywords: 'arquitectura docker django react celery redis postgres nginx servidor respaldo architecture server' },
  { slug: 'datos-y-sincronizacion', category: 'tecnico', icon: '🔄',
    title: { en: 'Data and syncing', es: 'Datos y sincronización' },
    excerpt: { en: 'Where cards, ban list, errata and Q&A come from.', es: 'De dónde salen las cartas, la ban list, la errata y las Q&A.' },
    keywords: 'sync bandai sincronizacion banlist errata rulings imagenes sync syncing banlist errata rulings images' },
  { slug: 'tareas-programadas', category: 'tecnico', icon: '⏰',
    title: { en: 'Scheduled tasks and alerts', es: 'Tareas programadas y avisos' },
    excerpt: { en: 'What runs on its own, when, and when you get a Telegram.', es: 'Qué se ejecuta solo, a qué hora, y cuándo te llega un Telegram.' },
    keywords: 'celery beat tareas cron telegram health salud monitorizacion tasks schedule health monitoring alerts' },
  { slug: 'despliegue', category: 'tecnico', icon: '🚢',
    title: { en: 'Development and deployment', es: 'Desarrollo y despliegue' },
    excerpt: { en: 'Running it locally, tests, CI and how it reaches the server.', es: 'Levantarlo en local, tests, CI y cómo se sube al servidor.' },
    keywords: 'desarrollo local docker compose tests ci github deploy despliegue development local tests deploy deployment' },
  { slug: 'api', category: 'tecnico', icon: '🔌',
    title: { en: 'REST API', es: 'API REST' },
    excerpt: { en: 'The public endpoints and the OpenAPI docs.', es: 'Los endpoints públicos y la documentación OpenAPI.' },
    keywords: 'api rest endpoints openapi swagger json api rest endpoints openapi swagger' },

  { slug: 'preguntas-frecuentes', category: 'ayuda', icon: '💬',
    title: { en: 'FAQ and troubleshooting', es: 'Preguntas frecuentes y problemas' },
    excerpt: { en: 'Quick answers and what to do when something does not work.', es: 'Respuestas rápidas y qué hacer cuando algo no funciona.' },
    keywords: 'faq ayuda problemas error no funciona camara precio faq help problems error not working camera price' },
]

const SOURCES = import.meta.glob('../../wiki/*/*.md', { query: '?raw', import: 'default', eager: true }) as Record<string, string>
const IMAGES = import.meta.glob('../../wiki/img/*', { query: '?url', import: 'default', eager: true }) as Record<string, string>

const LANG_KEY = 'wiki-lang'

/** Idioma de la wiki: el elegido con ES / EN (se recuerda) o, si no, el del navegador. */
export function initialLang(): WikiLang {
  try {
    const saved = localStorage.getItem(LANG_KEY)
    if (saved === 'es' || saved === 'en') return saved
  } catch {
    /* sin almacenamiento: el del navegador */
  }
  return navigator.language.toLowerCase().startsWith('es') ? 'es' : 'en'
}

export function saveLang(lang: WikiLang): void {
  try {
    localStorage.setItem(LANG_KEY, lang)
  } catch {
    /* no pasa nada: la próxima vez se usa el del navegador */
  }
}

export function imageUrl(name: string): string | undefined {
  return IMAGES[`../../wiki/img/${name}`]
}

export function articleBySlug(slug: string): WikiArticle | undefined {
  return WIKI_ARTICLES.find((a) => a.slug === slug)
}

export function wikiPath(slug?: string, anchor?: string): string {
  return `/wiki${slug ? `/${slug}` : ''}${anchor ? `#${anchor}` : ''}`
}

function source(slug: string, lang: WikiLang): string | undefined {
  return SOURCES[`../../wiki/${lang}/${slug}.md`]
}

/** Texto plano de un artículo (para el buscador de la wiki). */
export function articleText(slug: string, lang: WikiLang): string {
  return source(slug, lang) ?? ''
}

export function slugify(text: string): string {
  return text
    .toLowerCase()
    .normalize('NFD')
    .replace(/[̀-ͯ]/g, '')
    .replace(/[^a-z0-9\s-]/g, '')
    .trim()
    .replace(/\s+/g, '-')
}

const ALERTS: Record<WikiLang, Record<string, string>> = {
  es: { NOTE: 'Nota', TIP: 'Consejo', IMPORTANT: 'Importante', WARNING: 'Atención', CAUTION: 'Cuidado' },
  en: { NOTE: 'Note', TIP: 'Tip', IMPORTANT: 'Important', WARNING: 'Warning', CAUTION: 'Caution' },
}

export interface RenderedArticle {
  html: string
  toc: { id: string; text: string }[]
}

/** Markdown → HTML de la web: título fuera (lo pinta la página), enlaces e imágenes a sus rutas,
 * avisos de GitHub como recuadros y anclas en los apartados. */
export function renderArticle(slug: string, lang: WikiLang): RenderedArticle | null {
  const text = source(slug, lang)
  if (text == null) return null
  // El primer «# Título» ya sale en la cabecera de la página.
  const body = text.replace(/^# .*\n+/, '')
  const doc = new DOMParser().parseFromString(marked.parse(body, { async: false, gfm: true }), 'text/html')

  doc.querySelectorAll('img').forEach((img) => {
    const src = img.getAttribute('src') ?? ''
    const match = src.match(/^(?:\.\.?\/)?img\/(.+)$/)
    const url = match && imageUrl(match[1])
    if (url) img.setAttribute('src', url)
    img.setAttribute('loading', 'lazy')
    // Imagen sola en su párrafo: figura con su pie (el texto alternativo).
    const parent = img.parentElement
    if (parent?.tagName === 'P' && parent.childNodes.length === 1) {
      const figure = doc.createElement('figure')
      figure.className = 'wiki-figure'
      figure.appendChild(img.cloneNode())
      if (img.alt) {
        const caption = doc.createElement('figcaption')
        caption.textContent = img.alt
        figure.appendChild(caption)
      }
      parent.replaceWith(figure)
    }
  })

  doc.querySelectorAll('a[href]').forEach((a) => {
    const href = a.getAttribute('href') ?? ''
    const article = href.match(/^(?:\.\/)?([a-z0-9-]+)\.md(?:#(.+))?$/)
    if (article) a.setAttribute('href', wikiPath(article[1], article[2]))
    else if (href === 'README.md') a.setAttribute('href', wikiPath())
    else if (/^https?:/.test(href)) {
      a.setAttribute('target', '_blank')
      a.setAttribute('rel', 'noreferrer')
    }
  })

  doc.querySelectorAll('blockquote').forEach((quote) => {
    const first = quote.querySelector('p')
    const match = first?.innerHTML.match(/^\[!(NOTE|TIP|IMPORTANT|WARNING|CAUTION)\]\s*(<br>)?\s*/)
    if (!first || !match) return
    first.innerHTML = first.innerHTML.slice(match[0].length)
    if (!first.innerHTML.trim()) first.remove()
    const box = doc.createElement('div')
    box.className = `wiki-callout ${match[1].toLowerCase()}`
    const title = doc.createElement('strong')
    title.className = 'wiki-callout-title'
    title.textContent = ALERTS[lang][match[1]]
    box.append(title, ...Array.from(quote.childNodes))
    quote.replaceWith(box)
  })

  // Tablas anchas: que se desplacen dentro de su caja, no la página.
  doc.querySelectorAll('table').forEach((table) => {
    const wrap = doc.createElement('div')
    wrap.className = 'wiki-table'
    table.replaceWith(wrap)
    wrap.appendChild(table)
  })

  const toc: RenderedArticle['toc'] = []
  doc.querySelectorAll('h2, h3, h4').forEach((h) => {
    const id = slugify(h.textContent ?? '')
    h.id = id
    if (h.tagName === 'H2') toc.push({ id, text: h.textContent ?? '' })
  })
  return { html: doc.body.innerHTML, toc }
}
