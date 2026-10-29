import { useEffect, useMemo, useState } from 'react'
import CardModal from './components/CardModal'
import Pagination from './components/Pagination'
import { useOpenCard } from './lib/cardLink'
import { api } from './lib/api'
import { markNewsSeen, newsSeenAt } from './lib/news'
import { SkillIndex } from './lib/skills'
import type { CardChange, ChangesResponse } from './lib/types'

const dayFormat = new Intl.DateTimeFormat('es-ES', { weekday: 'long', day: 'numeric', month: 'long', year: 'numeric' })

/** Detalle de un cambio: qué había y qué hay ahora. */
function ChangeDetail({ change }: { change: CardChange }) {
  switch (change.kind) {
    case 'new':
      return <p className="muted small">Nueva en el catálogo.</p>
    case 'ruling':
      return <p className="news-text">{change.after}</p>
    case 'text':
    case 'errata':
      return (
        <div className="errata-cols">
          <div>
            <span className="errata-tag">Antes</span>
            <p>{change.before}</p>
          </div>
          <div>
            <span className="errata-tag after">Después</span>
            <p>{change.after}</p>
          </div>
        </div>
      )
    default:
      return (
        <p className="news-diff">
          {change.field && change.kind === 'stats' && <span className="muted">{change.field}: </span>}
          <span className="before">{change.before}</span> → <strong>{change.after}</strong>
        </p>
      )
  }
}

/** Novedades: cambios reales detectados al sincronizar con Bandai y la web oficial. */
export default function NewsPage() {
  const [data, setData] = useState<ChangesResponse | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [kinds, setKinds] = useState<string[]>([])
  const [page, setPage] = useState(1)
  const [openId, setOpenId] = useOpenCard()
  const [skills, setSkills] = useState<SkillIndex>(SkillIndex.empty)
  // Lo anterior a tu última visita no se marca como nuevo. Se lee una vez, al entrar.
  const [seenBefore] = useState(newsSeenAt)

  useEffect(() => {
    api.keywordSkills().then((d) => setSkills(new SkillIndex(d))).catch(() => {})
  }, [])

  useEffect(() => {
    api
      .changes(kinds, page)
      .then((d) => {
        setData(d)
        setError(null)
        const latest = d.results[0]?.created_at
        if (latest && page === 1 && !kinds.length) markNewsSeen(latest)
      })
      .catch((e: Error) => setError(e.message))
  }, [kinds, page])

  const days = useMemo(() => {
    const groups: [string, CardChange[]][] = []
    for (const change of data?.results ?? []) {
      const day = dayFormat.format(new Date(change.created_at))
      const last = groups[groups.length - 1]
      if (last && last[0] === day) last[1].push(change)
      else groups.push([day, [change]])
    }
    return groups
  }, [data])

  // Sin visita previa, todo es nuevo para ti.
  const unseen = (c: CardChange) => !seenBefore || Date.parse(c.created_at) > Date.parse(seenBefore)

  const toggleKind = (kind: string) => {
    setPage(1)
    setKinds((ks) => (ks.includes(kind) ? ks.filter((k) => k !== kind) : [...ks, kind]))
  }

  return (
    <main className="news-page">
      <div className="news-head">
        <h1>Novedades</h1>
        <p className="muted">
          Cambios detectados al sincronizar con Bandai y la web oficial: cartas nuevas, cambios de texto o imagen, banlist,
          erratas y preguntas oficiales.
        </p>
      </div>

      {data && (
        <div className="chips news-kinds">
          {data.kinds
            .filter((k) => k.count > 0)
            .map((k) => (
              <button
                key={k.kind}
                className={`chip news-kind ${k.kind} ${kinds.includes(k.kind) ? 'on' : ''}`}
                onClick={() => toggleKind(k.kind)}
                aria-pressed={kinds.includes(k.kind)}
              >
                {k.label} <span className="count">{k.count}</span>
              </button>
            ))}
          {kinds.length > 0 && (
            <button
              className="link small"
              onClick={() => {
                setPage(1)
                setKinds([])
              }}
            >
              ver todo
            </button>
          )}
        </div>
      )}

      {error && <p className="error">{error}</p>}
      {!data && !error && <p className="muted">Cargando…</p>}
      {data && data.count === 0 && <div className="empty">Aún no hay novedades: aparecerán tras el próximo sync.</div>}

      {days.map(([day, changes]) => (
        <section key={day} className="news-day">
          <h2>{day}</h2>
          <ul className="news-list">
            {changes.map((c) => (
              <li key={c.id} className={`news-item ${unseen(c) ? 'unseen' : ''}`}>
                <button
                  className="news-thumb"
                  onClick={() => c.card_id && setOpenId(c.card_id)}
                  disabled={!c.card_id}
                  aria-label={`Ver ${c.card_number} ${c.card_name}`}
                >
                  {c.thumb_url ? <img src={c.thumb_url} alt="" loading="lazy" /> : <span>{c.card_number}</span>}
                </button>
                <div className="news-body">
                  <div className="news-title">
                    <span className={`news-kind ${c.kind}`}>{c.kind_label}</span>
                    {unseen(c) && <span className="qa-new">nuevo</span>}
                    <button className="link" onClick={() => c.card_id && setOpenId(c.card_id)}>
                      {c.card_number} · {c.card_name}
                    </button>
                  </div>
                  <ChangeDetail change={c} />
                </div>
              </li>
            ))}
          </ul>
        </section>
      ))}

      {data && data.pages > 1 && <Pagination page={page} pages={data.pages} onPage={setPage} />}

      {openId !== null && (
        <CardModal
          key={openId}
          id={openId}
          onOpenPrint={setOpenId}
          skills={skills}
          onClose={() => setOpenId(null)}
          onFilter={(field, value) => {
            window.location.href = `/?add=${encodeURIComponent(field)}&value=${encodeURIComponent(value)}`
          }}
        />
      )}
    </main>
  )
}
