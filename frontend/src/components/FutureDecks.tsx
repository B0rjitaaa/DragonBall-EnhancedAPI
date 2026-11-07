// Locations → Decks → Future decks: mazos que quiero montar para jugarlos más adelante. Solo es la lista (no son
// ubicaciones ni tienen copias): se ve qué cartas tengo libres, cuáles están en otros mazos y cuáles faltan. Al
// montarlo, pasa por la importación de mazos con todas sus comprobaciones y deja de ser futuro.
import { useCallback, useEffect, useRef, useState } from 'react'
import DeckImport from './DeckImport'
import DeckPreviewDialog from './DeckPreviewDialog'
import { previewDeckCards } from '../lib/deckPreview'
import { api } from '../lib/api'
import { formatEur } from '../lib/prices'
import type { CardSummary, PlannedDeck, PlannedDeckDetail } from '../lib/types'
import { cardThumb } from '../lib/types'

export default function FutureDecks({ onBuilt }: { onBuilt: () => void }) {
  const [decks, setDecks] = useState<PlannedDeck[] | null>(null)
  const [catalog, setCatalog] = useState<Record<number, CardSummary>>({})
  const [error, setError] = useState('')
  const [adding, setAdding] = useState(false)
  const [open, setOpen] = useState<number | null>(null)
  const [building, setBuilding] = useState<PlannedDeckDetail | null>(null)

  const load = useCallback(
    () =>
      api
        .plannedDecks()
        .then((d) => {
          setDecks(d.results)
          setCatalog(d.catalog)
          setError('')
        })
        .catch((e: Error) => setError(e.message)),
    [],
  )
  useEffect(() => {
    void load()
  }, [load])

  return (
    <div className="future-decks">
      <h3 className="loc-sub future-head">
        <span>
          Future decks <small>{decks?.length ?? 0}</small>
          <span className="muted"> · lists you want to build and play; nothing moves until you build one</span>
        </span>
        <button className="btn" onClick={() => setAdding(true)}>
          + Future deck
        </button>
      </h3>
      {error && <p className="error small">{error}</p>}
      {decks && decks.length === 0 && (
        <p className="empty small">No future decks yet. Add one from a DeckPlanet / Top Deck Diffusion link or a pasted list.</p>
      )}
      {decks && decks.length > 0 && (
        <ul className="future-list">
          {decks.map((d) => {
            const leader = d.leader_bandai_id ? catalog[d.leader_bandai_id] : null
            const have = d.free + d.in_decks
            return (
              <li key={d.id}>
                <button className="future-row" onClick={() => setOpen(d.id)} title="See the list and what you have">
                  {leader ? <img src={cardThumb(leader)} alt="" loading="lazy" referrerPolicy="no-referrer" /> : <span className="locdeck-thumb-empty" />}
                  <span className="future-name">
                    <strong>{d.name}</strong>
                    <small className="muted">
                      {leader ? leader.name : 'No Leader'} · {d.main} Main{d.z ? ` · ${d.z} Z` : ''}
                      {d.side ? ` · ${d.side} side` : ''}
                    </small>
                  </span>
                  <span className="future-have">
                    <span className="future-bar" aria-hidden>
                      <i className="free" style={{ width: `${(100 * d.free) / Math.max(1, d.cards)}%` }} />
                      <i className="decks" style={{ width: `${(100 * d.in_decks) / Math.max(1, d.cards)}%` }} />
                    </span>
                    <small>
                      <b>{have}</b>/{d.cards} owned
                      {d.in_decks > 0 && <span className="muted"> · {d.in_decks} in other decks</span>}
                      {d.missing > 0 ? (
                        <span className="future-missing">
                          {' '}
                          · {d.missing} missing{d.cost > 0 && ` (~${formatEur(d.cost)})`}
                        </span>
                      ) : (
                        <span className="future-ok"> · you have every card</span>
                      )}
                    </small>
                  </span>
                </button>
              </li>
            )
          })}
        </ul>
      )}

      {adding && (
        <AddFutureDeck
          onClose={() => setAdding(false)}
          onSaved={() => {
            setAdding(false)
            void load()
          }}
        />
      )}
      {open != null && (
        <FutureDeckDialog
          id={open}
          onClose={() => setOpen(null)}
          onChanged={() => void load()}
          onBuild={(detail) => {
            setOpen(null)
            setBuilding(detail)
          }}
        />
      )}
      {building && (
        <DeckImport
          planned={{ id: building.planned.id, name: building.planned.name, source: building.planned.source, lines: building.lines }}
          onClose={() => {
            setBuilding(null)
            void load()
          }}
          onDone={() => {
            void load()
            onBuilt()
          }}
        />
      )}
    </div>
  )
}

/** Añadir un mazo futuro: un enlace (DeckPlanet, Top Deck Diffusion, Time Chamber) o la lista en texto. */
function AddFutureDeck({ onClose, onSaved }: { onClose: () => void; onSaved: () => void }) {
  const ref = useRef<HTMLDialogElement>(null)
  const [source, setSource] = useState('')
  const [name, setName] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  useEffect(() => ref.current?.showModal(), [])
  const save = (e: React.FormEvent) => {
    e.preventDefault()
    setBusy(true)
    setError('')
    api
      .createPlannedDeck({ source, name: name.trim() || undefined })
      .then(onSaved)
      .catch((err: Error) => setError(err.message))
      .finally(() => setBusy(false))
  }
  return (
    <dialog ref={ref} className="loc-dialog deck-import" onClose={onClose}>
      <form className="deck-import-body" onSubmit={save}>
        <header className="deck-import-head">
          <h2>New future deck</h2>
          <button type="button" className="icon-btn" onClick={() => ref.current?.close()} aria-label="Close">
            ✕
          </button>
        </header>
        <label className="loc-dialog-field">
          Deck link or list
          <textarea
            className="input"
            rows={8}
            value={source}
            autoFocus
            onChange={(e) => setSource(e.target.value)}
            placeholder={'https://www.dbs-deckplanet.com/…/deck/…\nhttps://topdeckdiffusion.com/decks/…\n\nor paste a list:\n1 Cell [EX20-01]\n4 Goku Black [BT29-086]'}
          />
        </label>
        <label className="loc-dialog-field">
          Name (optional)
          <input className="input" value={name} maxLength={120} onChange={(e) => setName(e.target.value)} placeholder="From the link, or the Leader's name" />
        </label>
        <p className="muted small">It only keeps the list: no cards move. You'll see which ones you have and which you're missing.</p>
        {error && <p className="error">{error}</p>}
        <div className="loc-dialog-actions">
          <button type="button" className="btn ghost" onClick={() => ref.current?.close()}>
            Cancel
          </button>
          <button className="btn primary" disabled={busy || !source.trim()}>
            {busy ? 'Saving…' : 'Save future deck'}
          </button>
        </div>
      </form>
    </dialog>
  )
}

/** El detalle de un mazo futuro: la vista de mazo con lo que tienes y lo que falta, y «Build this deck». */
function FutureDeckDialog({
  id,
  onClose,
  onChanged,
  onBuild,
}: {
  id: number
  onClose: () => void
  onChanged: () => void
  onBuild: (detail: PlannedDeckDetail) => void
}) {
  const [detail, setDetail] = useState<PlannedDeckDetail | null>(null)
  const [error, setError] = useState('')
  const [editing, setEditing] = useState<'name' | 'list' | null>(null)
  const [draft, setDraft] = useState('')
  const [confirmDelete, setConfirmDelete] = useState(false)
  const load = useCallback(
    () =>
      api
        .plannedDeck(id)
        .then(setDetail)
        .catch((e: Error) => setError(e.message)),
    [id],
  )
  useEffect(() => {
    void load()
  }, [load])

  if (!detail) {
    return error ? (
      <div className="review-zoom" onClick={onClose}>
        <p className="error">{error}</p>
      </div>
    ) : null
  }
  const p = detail.planned
  const { pool, side } = previewDeckCards(detail)
  const save = (body: { name?: string; source?: string }) =>
    api
      .updatePlannedDeck(id, body)
      .then(() => {
        setEditing(null)
        onChanged()
        return load()
      })
      .catch((e: Error) => setError(e.message))

  const actions = (
    <>
      <button type="button" className="btn primary" onClick={() => onBuild(detail)} title="Build it: the import checks run and the deck moves to your decks">
        🔨 Build this deck
      </button>
      <button type="button" className="btn" onClick={() => (setDraft(p.name), setEditing('name'))}>
        Rename
      </button>
      <button type="button" className="btn" onClick={() => (setDraft(''), setEditing('list'))}>
        Change list
      </button>
      {confirmDelete ? (
        <button
          type="button"
          className="btn danger"
          onClick={() =>
            api
              .deletePlannedDeck(id)
              .then(() => {
                onChanged()
                onClose()
              })
              .catch((e: Error) => setError(e.message))
          }
        >
          Yes, delete it
        </button>
      ) : (
        <button type="button" className="btn ghost" onClick={() => setConfirmDelete(true)}>
          Delete
        </button>
      )}
    </>
  )
  const have = p.free + p.in_decks
  const note = [
    `Future deck · from ${p.source_label} · nothing has been built: no cards moved.`,
    `You own ${have} of ${p.cards} copies (${p.free} free${p.in_decks ? `, ${p.in_decks} in other decks` : ''}).`,
    p.missing ? `${p.missing} missing${p.cost ? `, about ${formatEur(p.cost)}` : ''}.` : 'You have every card.',
    p.unknown.length ? `Not in the catalog: ${p.unknown.join(', ')}.` : '',
  ]
    .filter(Boolean)
    .join(' ')

  return (
    <DeckPreviewDialog
      name={p.name}
      pool={pool}
      side={side}
      note={note}
      onClose={onClose}
      title={<>☆ Future deck</>}
      eyebrow="Future deck · not built yet"
      back={<>← Back</>}
      actions={
        <>
          {actions}
          {editing && (
            <form
              className="future-edit"
              onSubmit={(e) => {
                e.preventDefault()
                void save(editing === 'name' ? { name: draft } : { source: draft })
              }}
            >
              {editing === 'name' ? (
                <input className="input" value={draft} autoFocus maxLength={120} onChange={(e) => setDraft(e.target.value)} />
              ) : (
                <textarea className="input" rows={6} value={draft} autoFocus onChange={(e) => setDraft(e.target.value)} placeholder="A new link or list for this deck" />
              )}
              <button className="btn primary" disabled={!draft.trim()}>
                Save
              </button>
              <button type="button" className="btn ghost" onClick={() => setEditing(null)}>
                Cancel
              </button>
              {error && <span className="error small">{error}</span>}
            </form>
          )}
        </>
      }
    />
  )
}
