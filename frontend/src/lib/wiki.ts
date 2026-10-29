import { marked } from 'marked'

/**
 * Wiki: los artículos son Markdown en frontend/wiki/ (se leen igual en GitHub) y aquí se
 * pintan en la web (/wiki y /wiki/<slug>). Las capturas viven en frontend/wiki/img/ (se
 * regeneran con scripts/wiki_screenshots.py).
 *
 * En el Markdown los enlaces van entre artículos (`modo-avanzado.md`, `precios.md#fuentes`)
 * y a imágenes (`img/buscador.jpg`): así funcionan en GitHub, y aquí se cambian por sus
 * rutas en la web. Los avisos usan la sintaxis de GitHub: `> [!TIP]`, `> [!NOTE]`,
 * `> [!WARNING]`, `> [!IMPORTANT]`.
 */

export interface WikiCategory {
  id: string
  icon: string
  label: string
  blurb: string
}

export interface WikiArticle {
  slug: string
  category: string
  icon: string
  title: string
  excerpt: string
  /** Captura de la tarjeta del índice (en wiki/img/). */
  cover?: string
  /** Palabras extra para el buscador de la wiki. */
  keywords?: string
}

export const WIKI_CATEGORIES: WikiCategory[] = [
  { id: 'empezar', icon: '🚀', label: 'Primeros pasos', blurb: 'Qué es la web, sus secciones y cómo moverte por ella.' },
  { id: 'instalacion', icon: '🧰', label: 'Instalación', blurb: 'Instalarlo con Docker, paso a paso, y todo lo que debe estar en marcha.' },
  { id: 'buscador', icon: '🔎', label: 'Buscador', blurb: 'Encontrar cualquier carta y entender su ficha.' },
  { id: 'coleccion', icon: '🗂️', label: 'Colección y mazos', blurb: 'Tus copias, dónde están y tus mazos.' },
  { id: 'escaner', icon: '📷', label: 'Escáner', blurb: 'Dar de alta cartas con la cámara del móvil.' },
  { id: 'precios', icon: '💶', label: 'Precios', blurb: 'De dónde sale cada precio y el valor de tu colección.' },
  { id: 'admin', icon: '🛠️', label: 'Administración', blurb: 'El admin de Django: revisión de precios, errores y copias.' },
  { id: 'tecnico', icon: '⚙️', label: 'Técnico', blurb: 'Arquitectura, servidores, tareas, despliegue y API.' },
  { id: 'ayuda', icon: '💬', label: 'Ayuda', blurb: 'Dudas frecuentes y qué hacer cuando algo falla.' },
]

// El orden de esta lista es el del índice y el de «Anterior / Siguiente».
export const WIKI_ARTICLES: WikiArticle[] = [
  { slug: 'bienvenida', category: 'empezar', icon: '👋', cover: 'buscador.jpg',
    title: 'Bienvenido a DragonBall EnhancedAPI',
    excerpt: 'Qué es esta web, qué secciones tiene y cómo está montada a grandes rasgos.',
    keywords: 'inicio menu secciones navegacion que es' },
  { slug: 'enlaces-y-navegacion', category: 'empezar', icon: '🔗', cover: 'enlace-carta.jpg',
    title: 'Enlaces, direcciones y atajos',
    excerpt: 'Cada búsqueda, carta y mazo tiene su propia dirección: cómo compartirlas y guardarlas.',
    keywords: 'url enlace compartir copiar direccion card favoritos' },

  { slug: 'instalacion', category: 'instalacion', icon: '🧰',
    title: 'Instalación paso a paso',
    excerpt: 'En tu ordenador, docker compose up y listo; en un servidor de casa, con HTTPS, copias y avisos.',
    keywords: 'instalar instalacion docker compose up env defaults requisitos servidor respaldo admin superuser main fingerprints https systemd backups cron' },
  { slug: 'servicios', category: 'instalacion', icon: '✅',
    title: 'Qué tiene que estar en marcha',
    excerpt: 'Contenedores, tareas, systemd y el equipo de respaldo: qué hace cada uno y cómo comprobarlo.',
    keywords: 'servicios contenedores docker ps celery beat worker systemd timer cron watchdog comprobar estado' },

  { slug: 'buscar-cartas', category: 'buscador', icon: '🔎', cover: 'buscador.jpg',
    title: 'Buscar cartas',
    excerpt: 'Búsqueda por texto, panel de filtros, orden y paginación.',
    keywords: 'buscar texto filtros facetas color energy power orden comillas excluir' },
  { slug: 'modo-avanzado', category: 'buscador', icon: '🧩', cover: 'modo-avanzado.jpg',
    title: 'Modo avanzado',
    excerpt: 'Combina condiciones con Y / O / NO para búsquedas que el panel no permite.',
    keywords: 'avanzado query builder grupos and or not condiciones operadores' },
  { slug: 'ficha-de-carta', category: 'buscador', icon: '🃏', cover: 'ficha-carta.jpg',
    title: 'La ficha de una carta',
    excerpt: 'Todo lo que muestra el detalle: texto, impresiones, precio, errata, Q&A y tus copias.',
    keywords: 'detalle modal carta leader awaken impresiones errata q&a ruling banned limited' },
  { slug: 'novedades', category: 'buscador', icon: '🆕', cover: 'novedades.jpg',
    title: 'Novedades',
    excerpt: 'Cartas nuevas y cambios del catálogo desde tu última visita.',
    keywords: 'novedades cambios nuevas sync bandai' },

  { slug: 'mi-coleccion', category: 'coleccion', icon: '🗂️', cover: 'coleccion.jpg',
    title: 'Mi colección',
    excerpt: 'Tus copias: añadir, quitar, mover, marcar falsas y ver cuánto vale todo.',
    keywords: 'coleccion copias cantidad falsas valor lista cuadricula' },
  { slug: 'ubicaciones', category: 'coleccion', icon: '📦', cover: 'ubicaciones.jpg',
    title: 'Ubicaciones',
    excerpt: 'Carpetas, cajas y mazos: dónde guardas cada copia.',
    keywords: 'ubicaciones carpeta caja binder mover orden' },
  { slug: 'mazos', category: 'coleccion', icon: '🃏', cover: 'mazo.jpg',
    title: 'Mazos',
    excerpt: 'Leader, Main Deck y Side Deck, versiones de la lista, partidas, estadísticas e histórico.',
    keywords: 'mazo deck leader side deck partidas estadisticas historico versiones archivar' },
  { slug: 'importar-exportar', category: 'coleccion', icon: '📤', cover: 'csv.jpg',
    title: 'Importar, exportar y copia de la colección',
    excerpt: 'CSV para hojas de cálculo, y la copia completa en JSON que se puede restaurar.',
    keywords: 'csv importar exportar copia backup json excel restaurar sustituir deshacer' },

  { slug: 'escaner', category: 'escaner', icon: '📷', cover: 'escaner.jpg',
    title: 'Usar el escáner',
    excerpt: 'Escanear desde el móvil, modo ráfaga y a qué ubicación van las cartas.',
    keywords: 'escaner camara movil rafaga https certificado' },
  { slug: 'revisar-escaneos', category: 'escaner', icon: '✅', cover: 'escaner.jpg',
    title: 'Revisar escaneos dudosos',
    excerpt: 'Qué hacer cuando el escáner no está seguro de la carta o de su edición.',
    keywords: 'revisar dudosos confirmar edicion alt art reconocer' },
  { slug: 'como-reconoce', category: 'escaner', icon: '🧠',
    title: 'Cómo reconoce las cartas',
    excerpt: 'Huellas de imagen, umbrales y desempates entre impresiones parecidas.',
    keywords: 'orb huella reconocimiento umbral impresiones fotos borrado' },

  { slug: 'precios', category: 'precios', icon: '💶', cover: 'precio-ficha.jpg',
    title: 'De dónde sale cada precio',
    excerpt: 'Cardmarket, TCGplayer y precios a mano: las reglas, paso a paso.',
    keywords: 'precio cardmarket tcgplayer trend ventas anuncio sospechoso manual' },
  { slug: 'pagina-precios', category: 'precios', icon: '📈', cover: 'precios.jpg',
    title: 'La página «Precios»',
    excerpt: 'Valor de la colección, su evolución y las cartas que más suben y bajan.',
    keywords: 'precios valor grafico radar suben bajan caras' },
  { slug: 'revisar-precios', category: 'precios', icon: '🧾', cover: 'admin-precios.jpg',
    title: 'Revisar precios en el admin',
    excerpt: 'Emparejar cartas sin producto, corregir dudosos y poner precios a mano.',
    keywords: 'revision precios admin emparejar dudosos manual falsa impresion' },

  { slug: 'admin', category: 'admin', icon: '🛠️', cover: 'admin.jpg',
    title: 'El admin de Django',
    excerpt: 'Qué hay en /admin/ y para qué sirve cada sección.',
    keywords: 'admin django usuario login secciones' },
  { slug: 'registro-de-errores', category: 'admin', icon: '🐞', cover: 'admin-errores.jpg',
    title: 'Registro de errores',
    excerpt: 'Los fallos de la web y del servidor, guardados y avisados por Telegram.',
    keywords: 'errores log errorlog telegram avisos' },
  { slug: 'copias-de-seguridad', category: 'admin', icon: '💾', cover: 'admin-copias.jpg',
    title: 'Copias de seguridad',
    excerpt: 'Copia diaria, copia bajo demanda desde el admin, retención y restauración.',
    keywords: 'backup copia seguridad restaurar pg_dump retencion' },

  { slug: 'arquitectura', category: 'tecnico', icon: '🏗️',
    title: 'Arquitectura',
    excerpt: 'Servicios, contenedores, servidores y cómo encajan.',
    keywords: 'arquitectura docker django react celery redis postgres nginx servidor respaldo' },
  { slug: 'datos-y-sincronizacion', category: 'tecnico', icon: '🔄',
    title: 'Datos y sincronización',
    excerpt: 'De dónde salen las cartas, la ban list, la errata y las Q&A.',
    keywords: 'sync bandai sincronizacion banlist errata rulings imagenes' },
  { slug: 'tareas-programadas', category: 'tecnico', icon: '⏰',
    title: 'Tareas programadas y avisos',
    excerpt: 'Qué se ejecuta solo, a qué hora, y cuándo te llega un Telegram.',
    keywords: 'celery beat tareas cron telegram health salud monitorizacion' },
  { slug: 'despliegue', category: 'tecnico', icon: '🚢',
    title: 'Desarrollo y despliegue',
    excerpt: 'Levantarlo en local, tests, CI y cómo se sube al servidor.',
    keywords: 'desarrollo local docker compose tests ci github deploy despliegue' },
  { slug: 'api', category: 'tecnico', icon: '🔌',
    title: 'API REST',
    excerpt: 'Los endpoints públicos y la documentación OpenAPI.',
    keywords: 'api rest endpoints openapi swagger json' },

  { slug: 'preguntas-frecuentes', category: 'ayuda', icon: '💬',
    title: 'Preguntas frecuentes y problemas',
    excerpt: 'Respuestas rápidas y qué hacer cuando algo no funciona.',
    keywords: 'faq ayuda problemas error no funciona camara precio' },
]

const SOURCES = import.meta.glob('../../wiki/*.md', { query: '?raw', import: 'default', eager: true }) as Record<string, string>
const IMAGES = import.meta.glob('../../wiki/img/*', { query: '?url', import: 'default', eager: true }) as Record<string, string>

export function imageUrl(name: string): string | undefined {
  return IMAGES[`../../wiki/img/${name}`]
}

export function articleBySlug(slug: string): WikiArticle | undefined {
  return WIKI_ARTICLES.find((a) => a.slug === slug)
}

export function wikiPath(slug?: string, anchor?: string): string {
  return `/wiki${slug ? `/${slug}` : ''}${anchor ? `#${anchor}` : ''}`
}

/** Texto plano de un artículo (para el buscador de la wiki). */
export function articleText(slug: string): string {
  return SOURCES[`../../wiki/${slug}.md`] ?? ''
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

const ALERTS: Record<string, string> = {
  NOTE: 'Nota',
  TIP: 'Consejo',
  IMPORTANT: 'Importante',
  WARNING: 'Atención',
  CAUTION: 'Cuidado',
}

export interface RenderedArticle {
  html: string
  toc: { id: string; text: string }[]
}

/** Markdown → HTML de la web: título fuera (lo pinta la página), enlaces e imágenes a sus rutas,
 * avisos de GitHub como recuadros y anclas en los apartados. */
export function renderArticle(slug: string): RenderedArticle | null {
  const source = SOURCES[`../../wiki/${slug}.md`]
  if (source == null) return null
  // El primer «# Título» ya sale en la cabecera de la página.
  const body = source.replace(/^# .*\n+/, '')
  const doc = new DOMParser().parseFromString(marked.parse(body, { async: false, gfm: true }), 'text/html')

  doc.querySelectorAll('img').forEach((img) => {
    const src = img.getAttribute('src') ?? ''
    const match = src.match(/^(?:\.\/)?img\/(.+)$/)
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
    title.textContent = ALERTS[match[1]]
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
