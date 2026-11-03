// Mis wants (/wants): las cartas que quiero comprar, la impresión exacta y cuántas copias, con su precio
// aproximado y lo que ya tengo de cada una. Se añaden desde el buscador (♡) o desde la ficha de la carta.
import { useEffect, useMemo, useState } from 'react'
import CardModal from './components/CardModal'
import { api } from './lib/api'
import { useOpenCard } from './lib/cardLink'
import { formatEur, priceLabel } from './lib/prices'
import { SkillIndex } from './lib/skills'
import type { WantsData } from './lib/types'
import { cardThumb } from './lib/types'
import { setWant, useWants } from './lib/wants'

type Sort = 'recent' | 'number' | 'price'
const SORTS: [Sort, string][] = [['recent', 'Recently added'], ['number', 'Card number'], ['price', 'Price']]

export default function WantsPage() {
  const [data, setData] = useState<WantsData | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [sort, setSort] = useState<Sort>('recent')
  const [query, setQuery] = useState('')
  const [pdfBusy, setPdfBusy] = useState(false)
  const [openId, setOpenId] = useOpenCard()
  const [skills, setSkills] = useState<SkillIndex>(SkillIndex.empty)
  // Las cantidades, al momento (también si se cambian en la ficha); la lista se vuelve a pedir al cerrarla.
  const wants = useWants()

  const load = () =>
    api
      .wants()
      .then((d) => {
        setData(d)
        setError(null)
      })
      .catch((e: Error) => setError(e.message))
  useEffect(() => {
    void load()
    api.keywordSkills().then((d) => setSkills(new SkillIndex(d))).catch(() => {})
  }, [])

  const q = query.trim().toLowerCase()
  const rows = useMemo(() => {
    if (!data) return []
    const list = data.wants
      .map((w) => ({ ...w, quantity: wants?.[w.bandai_id] ?? w.quantity, card: data.catalog[w.bandai_id] }))
      .filter((w) => w.card && (wants == null || wants[w.bandai_id]))
      .filter((w) => !q || `${w.card.name} ${w.card.card_number}`.toLowerCase().includes(q))
    if (sort === 'number') list.sort((a, b) => a.card.card_number.localeCompare(b.card.card_number, 'en', { numeric: true }))
    if (sort === 'price') list.sort((a, b) => (b.card.price?.eur ?? -1) - (a.card.price?.eur ?? -1))
    return list
  }, [data, wants, sort, q])
  const copies = rows.reduce((n, r) => n + r.quantity, 0)
  const cost = rows.reduce((n, r) => n + (r.card.price?.eur ?? 0) * r.quantity, 0)
  const noPrice = rows.filter((r) => r.card.price?.eur == null).length

  const change = (id: number, n: number) => void setWant(id, Math.max(0, Math.min(99, n))).catch((e: Error) => setError(e.message))

  // El PDF (lo que se ve: con la búsqueda y el orden). En el móvil se comparte directamente (WhatsApp…);
  // si el navegador no puede compartir ficheros, se descarga.
  const pdf = async (share: boolean) => {
    setPdfBusy(true)
    setError(null)
    try {
      const res = await fetch(api.wantsPdfUrl(query.trim(), sort))
      if (!res.ok) throw new Error(`Couldn't make the PDF (${res.status})`)
      const blob = await res.blob()
      const name = `my-wants-${new Date().toISOString().slice(0, 10)}.pdf`
      const file = new File([blob], name, { type: 'application/pdf' })
      if (share && navigator.canShare?.({ files: [file] })) {
        await navigator.share({ files: [file], title: 'My wants' }).catch((e: Error) => {
          if (e.name !== 'AbortError') throw e
        })
      } else {
        const url = URL.createObjectURL(blob)
        const a = Object.assign(document.createElement('a'), { href: url, download: name })
        a.click()
        setTimeout(() => URL.revokeObjectURL(url), 10_000)
      }
    } catch (e) {
      setError((e as Error).message)
    } finally {
      setPdfBusy(false)
    }
  }
  const canShareFiles = typeof navigator.canShare === 'function' && navigator.canShare({ files: [new File([''], 'x.pdf', { type: 'application/pdf' })] })

  return (
    <main className="wants-page">
      <header className="wants-head">
        <div>
          <h1>My wants</h1>
          <p className="muted">
            Cards you want to buy. Add them with ♡ on a card in Search or from its details. Prices are approximate (Cardmarket).
          </p>
        </div>
        {(data?.wants.length ?? 0) > 0 && (
          <div className="segmented" role="group" aria-label="Sort by">
            {SORTS.map(([key, label]) => (
              <button key={key} className={sort === key ? 'on' : ''} onClick={() => setSort(key)}>
                {label}
              </button>
            ))}
          </div>
        )}
      </header>

      {(data?.wants.length ?? 0) > 0 && (
        <div className="wants-tools">
          <input
            className="input"
            type="search"
            placeholder="Search your wants by name or number…"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            aria-label="Search your wants"
          />
          {canShareFiles && (
            <button className="btn primary" onClick={() => void pdf(true)} disabled={pdfBusy || rows.length === 0}>
              {pdfBusy ? 'Making the PDF…' : '↗ Share PDF'}
            </button>
          )}
          <button className={`btn ${canShareFiles ? '' : 'primary'}`} onClick={() => void pdf(false)} disabled={pdfBusy || rows.length === 0}>
            {pdfBusy && !canShareFiles ? 'Making the PDF…' : '⇩ Download PDF'}
          </button>
        </div>
      )}

      {error && <p className="error">{error}</p>}
      {!data && !error && <p className="muted">Loading…</p>}

      {data && data.wants.length > 0 && rows.length === 0 && q && <p className="empty">No wants match “{query.trim()}”.</p>}
      {data && data.wants.length === 0 && (
        <p className="empty">
          No wants yet. In <a href="/">Search</a>, tap ♡ on a card (or “♡ Add to my wants” in its details) to add it here.
        </p>
      )}

      {rows.length > 0 && (
        <>
          <p className="wants-total">
            <strong>{rows.length}</strong> {rows.length === 1 ? 'card' : 'cards'} · <strong>{copies}</strong>{' '}
            {copies === 1 ? 'copy' : 'copies'} · about <strong>{formatEur(cost)}</strong>
            {noPrice > 0 && <span className="muted"> ({noPrice} without a price)</span>}
          </p>
          <ul className="wants-grid">
            {rows.map((w) => (
              <li key={w.bandai_id} className="want-card">
                <button className="want-img" onClick={() => setOpenId(w.bandai_id)} title={`${w.card.card_number} · ${w.card.name}`}>
                  <img src={cardThumb(w.card)} alt={w.card.name} loading="lazy" referrerPolicy="no-referrer" />
                </button>
                <div className="want-body">
                  <strong className="want-name">{w.card.name}</strong>
                  <span className="muted small">
                    {w.card.card_number}
                    {w.card.rarity_code && ` · ${w.card.rarity_code}`}
                    {w.card.price && ` · ${priceLabel(w.card.price)}`}
                  </span>
                  {(w.owned > 0 || w.owned_other_prints > 0) && (
                    <span className="want-owned small">
                      You have {w.owned > 0 && `${w.owned} of this print`}
                      {w.owned > 0 && w.owned_other_prints > 0 && ' and '}
                      {w.owned_other_prints > 0 && `${w.owned_other_prints} of another print`}
                    </span>
                  )}
                  <span className="want-controls">
                    <span className="owned-qty">
                      <button className="qty-btn" onClick={() => change(w.bandai_id, w.quantity - 1)} aria-label={`Want one ${w.card.name} less`}>
                        −
                      </button>
                      <strong title="Copies you want">×{w.quantity}</strong>
                      <button className="qty-btn" onClick={() => change(w.bandai_id, w.quantity + 1)} disabled={w.quantity >= 99} aria-label={`Want one more ${w.card.name}`}>
                        +
                      </button>
                    </span>
                    <button className="link small" onClick={() => change(w.bandai_id, 0)}>
                      Remove
                    </button>
                  </span>
                </div>
              </li>
            ))}
          </ul>
        </>
      )}

      {openId !== null && (
        <CardModal
          key={openId}
          id={openId}
          onOpenPrint={setOpenId}
          skills={skills}
          onClose={() => {
            setOpenId(null)
            void load() // una impresión añadida desde la ficha
          }}
          onFilter={(field, value) => {
            window.location.href = `/?add=${encodeURIComponent(field)}&value=${encodeURIComponent(value)}`
          }}
        />
      )}
    </main>
  )
}
