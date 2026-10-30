import { useEffect, useRef, useState } from 'react'
import { KIND_LABELS } from './OwnedPanel'
import { api } from '../lib/api'
import { cardThumb, type CardSummary, type PickGroup, type SavedPickList } from '../lib/types'

/** La lista en texto (para copiarla al móvil, a una nota…). */
function asText(deckName: string, groups: PickGroup[]): string {
  const lines = [`Cards to fetch for “${deckName}”`]
  for (const g of groups) {
    lines.push('', g.kind === 'out' ? g.location : `${g.location} (${KIND_LABELS[g.kind] ?? g.kind})`)
    for (const c of g.cards) {
      const where = [c.position ? `#${c.position}` : '', ...c.notes].filter(Boolean).join(' · ')
      lines.push(`- ${c.quantity}× ${c.name} [${c.number}${c.rarity ? ` ${c.rarity}` : ''}]${where ? ` — ${where}` : ''}`)
    }
  }
  return `${lines.join('\n')}\n`
}

/** Dónde coger cada copia que ha pasado al mazo: por caja / archivador / mazo, en el orden en que están, con su
 * posición, para ir marcándolas mientras las sacas. */
export default function PickList({
  deckId, deckName, groups, catalog, initialDone = [], onRemoved,
}: {
  /** Mazo al que pertenece: lo marcado se guarda y la lista se puede quitar. */
  deckId?: number
  deckName: string
  groups: PickGroup[]
  catalog: Record<number, CardSummary>
  initialDone?: string[]
  onRemoved?: () => void
}) {
  const [done, setDone] = useState<Set<string>>(() => new Set(initialDone))
  const [saveError, setSaveError] = useState<string | null>(null)
  const [copy, setCopy] = useState<'idle' | 'copied' | 'manual'>('idle')
  const total = groups.reduce((n, g) => n + g.cards.length, 0)
  if (!total) return null
  const toggle = (key: string) => {
    const next = new Set(done)
    if (next.has(key)) next.delete(key)
    else next.add(key)
    setDone(next)
    if (deckId != null) {
      api.savePicked(deckId, [...next]).then(() => setSaveError(null), (e: Error) => setSaveError(`Couldn't save: ${e.message}`))
    }
  }
  const remove = async () => {
    if (deckId == null) return
    try {
      await api.deletePickList(deckId)
      onRemoved?.()
    } catch (e) {
      setSaveError((e as Error).message)
    }
  }
  const copyList = async () => {
    try {
      await navigator.clipboard.writeText(asText(deckName, groups))
      setCopy('copied')
      window.setTimeout(() => setCopy('idle'), 2000)
    } catch {
      setCopy('manual')
    }
  }
  return (
    <section className="pick-list">
      <div className="pick-list-head">
        <h3>
          Where to get the cards <small>{done.size}/{total} picked</small>
        </h3>
        <span className="pick-list-tools">
          <button type="button" className="btn small ghost" onClick={copyList}>
            {copy === 'copied' ? 'Copied ✓' : 'Copy list'}
          </button>
          {deckId != null && done.size < total && (
            <button type="button" className="btn small ghost" onClick={() => void remove()} title="Forget this list (the cards stay in the deck)">
              Remove
            </button>
          )}
        </span>
      </div>
      <p className="muted small">
        The site has already moved them to the deck: take them out of each place and tick them off. <strong>#N</strong> is
        the card's place in that location's “My order”.
        {deckId != null && ' Your ticks are saved: you can come back to this list from the deck.'}
      </p>
      {saveError && <p className="error small">{saveError}</p>}
      {deckId != null && done.size === total && (
        <div className="pick-list-finished">
          ✔ All picked.
          <button type="button" className="btn small primary" onClick={() => void remove()}>
            Remove the list
          </button>
        </div>
      )}
      {copy === 'manual' && (
        <textarea className="input pick-list-text" readOnly rows={6} value={asText(deckName, groups)} onFocus={(e) => e.currentTarget.select()} autoFocus />
      )}
      {groups.map((g) => (
        <div key={g.location_id} className="pick-group">
          <h4 className={g.kind === 'out' ? 'pick-out' : ''}>
            {g.location} {g.kind !== 'out' && <small>{KIND_LABELS[g.kind] ?? g.kind}</small>}
          </h4>
          <ul>
            {g.cards.map((c) => {
              const key = `${g.location_id}-${c.bandai_id}`
              const card = catalog[c.bandai_id]
              return (
                <li key={key} className={done.has(key) ? 'done' : ''}>
                  <label>
                    <input type="checkbox" checked={done.has(key)} onChange={() => toggle(key)} />
                    {card && <img src={cardThumb(card)} alt="" loading="lazy" referrerPolicy="no-referrer" />}
                    <span className="pick-card">
                      <strong>
                        {c.quantity}× {c.name}
                      </strong>
                      <small>
                        {c.number}
                        {c.rarity && ` · ${c.rarity}`}
                      </small>
                    </span>
                    <span className="pick-where">
                      {c.position != null && <span className="pick-pos">#{c.position}</span>}
                      {c.notes.map((n) => (
                        <span key={n} className="pick-note">
                          {n}
                        </span>
                      ))}
                      {c.notes.length > c.quantity && <small className="muted">any {c.quantity} of these</small>}
                    </span>
                  </label>
                </li>
              )
            })}
          </ul>
        </div>
      ))}
    </section>
  )
}

/** La lista de recogida guardada de un mazo, en una ventana (se abre desde el mazo). */
export function PickListDialog({ deckId, onClose }: { deckId: number; onClose: () => void }) {
  const ref = useRef<HTMLDialogElement>(null)
  const [data, setData] = useState<SavedPickList | null>(null)
  const [error, setError] = useState<string | null>(null)
  useEffect(() => {
    ref.current?.showModal()
    api.pickList(deckId).then(setData, (e: Error) => setError(e.message))
  }, [deckId])
  return (
    <dialog ref={ref} className="loc-dialog deck-import" onClose={onClose}>
      <div className="deck-import-body">
        <header className="deck-import-head">
          <h2>Cards to fetch</h2>
          <button type="button" className="icon-btn" onClick={() => ref.current?.close()} aria-label="Close">
            ✕
          </button>
        </header>
        {error && <p className="error">{error}</p>}
        {!data && !error && <p className="muted">Loading…</p>}
        {data && (
          <PickList
            deckId={deckId}
            deckName={data.deck}
            groups={data.groups}
            catalog={data.catalog}
            initialDone={data.done}
            onRemoved={() => ref.current?.close()}
          />
        )}
      </div>
    </dialog>
  )
}
