// Tools → Printings review (/tools/printings): las versiones que tiene DeckPlanet y quizá nosotros no. Carta a carta,
// sus versiones al lado de las nuestras; cada una se marca «nos falta», «la tenemos» o «ignorar».
import { useEffect, useState } from 'react'
import { api } from './lib/api'
import type { PrintingReviewGroup, PrintingReviewPage as Data, ReviewMark } from './lib/types'
import { cardThumb } from './lib/types'

const MARKS: { mark: ReviewMark; label: string; title: string }[] = [
  { mark: 'missing', label: '✗', title: "Missing: we don't have this version" },
  { mark: 'have', label: '✓', title: 'Have: we already have it (maybe with another picture)' },
  { mark: 'ignore', label: '–', title: 'Ignore: not worth adding (e.g. a duplicate on their side)' },
]

export default function PrintingReviewPage() {
  const [data, setData] = useState<Data | null>(null)
  const [error, setError] = useState('')
  const [series, setSeries] = useState('')
  const [kind, setKind] = useState('')
  const [mark, setMark] = useState('pending')
  const [typed, setTyped] = useState('')
  const [q, setQ] = useState('')
  const [page, setPage] = useState(1)
  const [zoom, setZoom] = useState<string | null>(null)

  useEffect(() => {
    const t = window.setTimeout(() => setQ(typed.trim()), 300)
    return () => window.clearTimeout(t)
  }, [typed])
  const key = JSON.stringify({ series, kind, mark, q })
  const [lastKey, setLastKey] = useState(key)
  if (key !== lastKey) {
    setLastKey(key)
    setPage(1)
  }
  useEffect(() => {
    const ctrl = new AbortController()
    api
      .printingReview({ series, kind, mark, q, page }, ctrl.signal)
      .then((d) => {
        setData(d)
        setError('')
      })
      .catch((e: Error) => e.name !== 'AbortError' && setError(e.message))
    return () => ctrl.abort()
  }, [series, kind, mark, q, page])
  useEffect(() => {
    // En Chrome reciente scrollTo devuelve una Promise: no puede ser el valor de retorno del efecto.
    window.scrollTo({ top: 0 })
  }, [page])
  useEffect(() => {
    if (!zoom) return
    const onKey = (e: KeyboardEvent) => e.key === 'Escape' && setZoom(null)
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [zoom])

  // Marcar al momento en la página (y en los totales); si falla, se vuelve a pedir.
  const setOne = (groupNumber: string, id: number, next: ReviewMark) => {
    setData((d) => {
      if (!d) return d
      let before: ReviewMark = ''
      const results = d.results.map((g) =>
        g.number !== groupNumber
          ? g
          : {
              ...g,
              theirs: g.theirs.map((v) => {
                if (v.id !== id) return v
                before = v.mark
                return { ...v, mark: next }
              }),
            },
      )
      const totals = { ...d.totals }
      totals[before || 'pending'] -= 1
      totals[next || 'pending'] += 1
      return { ...d, results, totals }
    })
    api.markPrinting(id, next).catch((e: Error) => setError(e.message))
  }
  const markRest = (g: PrintingReviewGroup, next: ReviewMark) => g.theirs.filter((v) => !v.mark).forEach((v) => setOne(g.number, v.id, next))

  const t = data?.totals
  const done = t ? t.versions - t.pending : 0
  return (
    <main className="tools-page review-page">
      <header>
        <p className="muted small">
          <a className="link" href="/tools">
            Tools
          </a>{' '}
          ›
        </p>
        <h1>Printings review</h1>
        <p className="muted">
          Versions DeckPlanet has for cards where we have fewer (or none). DeckPlanet doesn’t say how its versions differ, so compare the
          pictures and mark each of theirs: <b>✗</b> we don’t have it, <b>✓</b> we have it, <b>–</b> ignore. Click a picture to see it big.
        </p>
      </header>

      {t && (
        <section className="tools-card review-progress">
          <div className="review-bar" aria-label={`${done} of ${t.versions} reviewed`}>
            <i className="missing" style={{ width: `${(100 * t.missing) / t.versions}%` }} />
            <i className="have" style={{ width: `${(100 * t.have) / t.versions}%` }} />
            <i className="ignore" style={{ width: `${(100 * t.ignore) / t.versions}%` }} />
          </div>
          <p className="small">
            <b>{done}</b> of {t.versions} versions reviewed ({t.cards} cards) · <span className="rv-missing">✗ {t.missing} missing</span> ·{' '}
            <span className="rv-have">✓ {t.have} have</span> · <span className="muted">– {t.ignore} ignored</span> · {t.pending} pending
          </p>
        </section>
      )}

      <section className="tools-card">
        <div className="review-filters">
          <input className="input" type="search" value={typed} onChange={(e) => setTyped(e.target.value)} placeholder="Search a number or name…" />
          <select className="input" value={mark} onChange={(e) => setMark(e.target.value)} aria-label="Show">
            <option value="pending">With versions to review</option>
            <option value="missing">With a version we lack</option>
            <option value="have">With a version we have</option>
            <option value="ignore">With an ignored version</option>
            <option value="">All cards</option>
          </select>
          <select className="input" value={series} onChange={(e) => setSeries(e.target.value)} aria-label="Series">
            <option value="">All series</option>
            {data?.series.map((s) => (
              <option key={s} value={s}>
                {s}
              </option>
            ))}
          </select>
          <select className="input" value={kind} onChange={(e) => setKind(e.target.value)} aria-label="Kind">
            <option value="">Fewer versions and not in the catalog</option>
            <option value="fewer">We have fewer versions</option>
            <option value="absent">Not in our catalog (BT32, new promos)</option>
          </select>
        </div>
        {error && <p className="error small">{error}</p>}
        {!data && !error && <p className="muted small">Loading…</p>}
        {data && data.results.length === 0 && <p className="muted small">Nothing here with these filters.</p>}
        <div className="review-list">
          {data?.results.map((g) => (
            <article key={g.number} className="review-card">
              <header>
                <b>{g.number}</b> {g.name}
                <span className="hx-tag">{g.kind === 'absent' ? 'not in our catalog' : `DeckPlanet ${g.their_versions} · ours ${g.our_versions}`}</span>
                {g.theirs.some((v) => !v.mark) && (
                  <span className="review-rest">
                    Rest:
                    <button className="link small" onClick={() => markRest(g, 'have')}>
                      ✓ have
                    </button>
                    <button className="link small" onClick={() => markRest(g, 'missing')}>
                      ✗ missing
                    </button>
                  </span>
                )}
              </header>
              <div className="review-cols">
                <div>
                  <h4>DeckPlanet</h4>
                  <div className="review-imgs">
                    {g.theirs.map((v) => (
                      <figure key={v.id} className={`review-version ${v.mark || 'pending'}`}>
                        <button type="button" className="review-img" onClick={() => setZoom(v.image_url)} title="See it big">
                          <img src={v.image_url} alt={v.code} loading="lazy" />
                        </button>
                        <figcaption>{v.code}</figcaption>
                        <div className="review-marks">
                          {MARKS.map((m) => (
                            <button
                              key={m.mark}
                              type="button"
                              className={`rv-${m.mark} ${v.mark === m.mark ? 'on' : ''}`}
                              title={m.title}
                              aria-label={m.title.split(':')[0]}
                              aria-pressed={v.mark === m.mark}
                              onClick={() => setOne(g.number, v.id, v.mark === m.mark ? '' : m.mark)}
                            >
                              {m.label}
                            </button>
                          ))}
                        </div>
                      </figure>
                    ))}
                  </div>
                </div>
                <div>
                  <h4>Ours</h4>
                  {g.ours.length === 0 ? (
                    <p className="muted small">Not in our catalog.</p>
                  ) : (
                    <div className="review-imgs">
                      {g.ours.map((o) => (
                        <figure key={o.id} className="review-version ours">
                          <button type="button" className="review-img" onClick={() => o.image_url && setZoom(o.image_url)} title="See it big">
                            {o.image_url ? (
                              <img src={cardThumb(o as never)} alt={o.rarity} loading="lazy" referrerPolicy="no-referrer" />
                            ) : (
                              <span className="review-noimg">No picture</span>
                            )}
                          </button>
                          <figcaption>
                            {o.rarity}
                            <small>{o.card_set}</small>
                          </figcaption>
                        </figure>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            </article>
          ))}
        </div>
        {data && data.pages > 1 && (
          <div className="hx-pager">
            <button className="btn small" disabled={page <= 1} onClick={() => setPage(page - 1)}>
              ‹ Previous
            </button>
            <span className="muted small">
              Page {page} of {data.pages} · {data.count} cards
            </span>
            <button className="btn small" disabled={page >= data.pages} onClick={() => setPage(page + 1)}>
              Next ›
            </button>
          </div>
        )}
      </section>
      {zoom && (
        <div className="review-zoom" onClick={() => setZoom(null)} role="dialog" aria-label="Card picture">
          <img src={zoom} alt="" referrerPolicy="no-referrer" />
        </div>
      )}
    </main>
  )
}
