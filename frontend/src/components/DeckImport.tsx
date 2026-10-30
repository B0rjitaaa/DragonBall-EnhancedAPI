import { useEffect, useRef, useState } from 'react'
import { api } from '../lib/api'
import { formatEur } from '../lib/prices'
import { locationPath } from '../lib/query'
import PickList from './PickList'
import { cardThumb, type DeckImportPreview, type DeckImportResult, type DeckImportRow } from '../lib/types'

const SECTION_LABEL: Record<string, string> = { leader: 'Leader', main: 'Main', z: 'Z', side: 'Side' }

/** Importar un mazo: pegar el enlace (DeckPlanet, Top Deck Diffusion, Time Chamber) o la lista en texto → ver qué
 * tienes libre, qué está en otros mazos (y elegir de cuáles coger) y qué falta → crear el mazo. */
export default function DeckImport({ onClose, onDone }: { onClose: () => void; onDone: () => void }) {
  const ref = useRef<HTMLDialogElement>(null)
  const [source, setSource] = useState('')
  const [preview, setPreview] = useState<DeckImportPreview | null>(null)
  const [name, setName] = useState('')
  const [takeFrom, setTakeFrom] = useState<Set<number>>(() => new Set())
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [result, setResult] = useState<DeckImportResult | null>(null)

  useEffect(() => {
    ref.current?.showModal()
  }, [])

  const check = async () => {
    setBusy(true)
    setError(null)
    try {
      const data = await api.previewDeckImport(source)
      setPreview(data)
      setName(data.name)
      setTakeFrom(new Set())
    } catch (e) {
      setError((e as Error).message)
    } finally {
      setBusy(false)
    }
  }

  const create = async () => {
    if (!preview) return
    setBusy(true)
    setError(null)
    try {
      setResult(await api.importDeck(preview.lines, name, preview.source, [...takeFrom]))
      onDone()
    } catch (e) {
      setError((e as Error).message)
    } finally {
      setBusy(false)
    }
  }

  // Lo que falta según los mazos elegidos (las copias de los mazos no elegidos también faltan).
  const missingNow = (r: DeckImportRow) => r.missing + r.in_use.filter((u) => !takeFrom.has(u.deck_id)).reduce((n, u) => n + u.quantity, 0)
  const totals = preview && {
    taken: preview.rows.reduce((n, r) => n + r.in_use.filter((u) => takeFrom.has(u.deck_id)).reduce((m, u) => m + u.quantity, 0), 0),
    missing: preview.rows.reduce((n, r) => n + missingNow(r), 0),
    cost: preview.rows.reduce((sum, r) => sum + missingNow(r) * (preview.catalog[r.bandai_id]?.price?.eur ?? 0), 0),
  }

  const toggle = (deckId: number) =>
    setTakeFrom((s) => {
      const next = new Set(s)
      if (next.has(deckId)) next.delete(deckId)
      else next.add(deckId)
      return next
    })

  return (
    <dialog ref={ref} className="loc-dialog deck-import" onClose={onClose} onCancel={(e) => busy && e.preventDefault()}>
      <div className="deck-import-body">
        <header className="deck-import-head">
          <h2>Import a deck</h2>
          <button type="button" className="icon-btn" onClick={() => ref.current?.close()} disabled={busy} aria-label="Close">
            ✕
          </button>
        </header>

        {result ? (
          <div className="deck-import-done">
            <p>
              ✔ <strong>“{result.deck.name}”</strong> is ready: <strong>{result.moved}</strong> copies moved into it
              {result.missing > 0 && (
                <>
                  , <strong>{result.missing}</strong> still missing (they're in its list so you can see them)
                </>
              )}
              .
            </p>
            <PickList deckId={result.deck.id} deckName={result.deck.name} groups={result.pick_list} catalog={result.catalog} />
            {result.decks_changed.length > 0 && (
              <ul className="deck-import-changed">
                {result.decks_changed.map((d) => (
                  <li key={d.deck_id}>
                    “{d.deck}” gave {d.copies} {d.copies === 1 ? 'copy' : 'copies'} and saved version {d.version} with what it
                    has left.
                  </li>
                ))}
              </ul>
            )}
            <div className="loc-dialog-actions">
              <button type="button" className="btn ghost" onClick={() => ref.current?.close()}>
                Close
              </button>
              <a className="btn primary" href={locationPath({ uid: result.deck.uid, kind: 'deck' })}>
                Open the deck →
              </a>
            </div>
          </div>
        ) : !preview ? (
          <form
            onSubmit={(e) => {
              e.preventDefault()
              void check()
            }}
          >
            <label>
              Deck link or deck list
              <textarea
                className="input"
                rows={7}
                autoFocus
                value={source}
                onChange={(e) => setSource(e.target.value)}
                placeholder={'https://www.dbs-deckplanet.com/…/deck/…\nhttps://topdeckdiffusion.com/decks/…\n\nor paste a list:\n1 Cell [EX20-01]\n4 Goku Black [BT29-086]\n4x BT10-088'}
              />
            </label>
            <p className="muted small">
              Links from <strong>DeckPlanet</strong>, <strong>Top Deck Diffusion</strong> and <strong>Time Chamber</strong>.
              From any other site, use its “export” or “copy list” option and paste the text. Any printing of a card
              counts; fake copies don't.
            </p>
            {error && <p className="error">{error}</p>}
            <div className="loc-dialog-actions">
              <button type="button" className="btn ghost" onClick={() => ref.current?.close()}>
                Cancel
              </button>
              <button className="btn primary" disabled={busy || !source.trim()}>
                {busy ? 'Checking…' : 'Check the list'}
              </button>
            </div>
          </form>
        ) : (
          <div className="deck-import-preview">
            <p className="muted small">
              From {preview.source_label} · {preview.totals.cards} cards
              {!preview.has_leader && <strong className="deck-import-warn"> · no Leader in the list</strong>}
            </p>
            <label>
              Deck name
              <input className="input" value={name} maxLength={80} onChange={(e) => setName(e.target.value)} placeholder="e.g. Goku Black" />
            </label>

            <div className="deck-import-totals">
              <span className="ok">
                <strong>{preview.totals.free}</strong> free
              </span>
              <span className="use">
                <strong>{preview.totals.in_use}</strong> in other decks
              </span>
              <span className="miss">
                <strong>{totals?.missing ?? 0}</strong> missing
                {!!totals?.cost && <small> · ≈ {formatEur(totals.cost)}</small>}
              </span>
            </div>

            {preview.in_use.length > 0 && (
              <div className="deck-import-alert" role="alert">
                <strong>⚠ Some cards are in use in other decks</strong>
                <p className="small">
                  Tick a deck to take its copies: they move to “{name || 'the new deck'}” and that deck saves a new version
                  with what it has left. Untick it and those cards count as missing.
                </p>
                {preview.in_use.map((d) => (
                  <label key={d.deck_id} className={`deck-import-deck ${takeFrom.has(d.deck_id) ? 'on' : ''}`}>
                    <input type="checkbox" checked={takeFrom.has(d.deck_id)} onChange={() => toggle(d.deck_id)} />
                    <span>
                      Take {d.copies} {d.copies === 1 ? 'copy' : 'copies'} from <strong>“{d.deck}”</strong>
                      <small>{d.cards.map((c) => `${c.quantity}× ${c.name} (${c.number})`).join(' · ')}</small>
                    </span>
                  </label>
                ))}
              </div>
            )}

            <ul className="deck-import-rows">
              {preview.rows.map((r) => {
                const card = preview.catalog[r.bandai_id]
                const missing = missingNow(r)
                const taken = r.in_use.filter((u) => takeFrom.has(u.deck_id)).reduce((n, u) => n + u.quantity, 0)
                const blocked = r.in_use.filter((u) => !takeFrom.has(u.deck_id))
                return (
                  <li key={r.number} className={missing ? 'miss' : taken ? 'use' : 'ok'}>
                    {card && <img src={cardThumb(card)} alt="" loading="lazy" referrerPolicy="no-referrer" />}
                    <span className="deck-import-card">
                      <strong>
                        {r.quantity}× {r.name}
                      </strong>
                      <small>
                        {r.number} · {Object.entries(r.sections).map(([s, n]) => `${SECTION_LABEL[s]} ${n}`).join(' · ')}
                      </small>
                    </span>
                    <span className="deck-import-status">
                      {r.free > 0 && (
                        <span className="ok" title={r.from.map((f) => `${f.quantity} in “${f.location}”`).join(' · ')}>
                          ✓ {r.free} free <small>({r.from.map((f) => `${f.location}${r.from.length > 1 || f.quantity !== r.free ? ` ×${f.quantity}` : ''}`).join(', ')})</small>
                        </span>
                      )}
                      {taken > 0 && <span className="use">↺ {taken} from other decks</span>}
                      {blocked.map((u) => (
                        <span key={u.deck_id} className="use dim">
                          {u.quantity} in “{u.deck}”
                        </span>
                      ))}
                      {missing > 0 && <span className="miss">✕ {missing} missing</span>}
                    </span>
                  </li>
                )
              })}
            </ul>

            {(preview.unknown.length > 0 || preview.unread.length > 0) && (
              <p className="csv-warn small">
                {preview.unknown.length > 0 && <>Not in the catalog (skipped): {preview.unknown.join(', ')}. </>}
                {preview.unread.length > 0 && <>Lines not understood: {preview.unread.slice(0, 5).join(' · ')}</>}
              </p>
            )}
            {error && <p className="error">{error}</p>}
            <div className="loc-dialog-actions">
              <button type="button" className="btn ghost" onClick={() => setPreview(null)} disabled={busy}>
                ← Back
              </button>
              <span className="spacer" />
              <button type="button" className="btn primary" onClick={() => void create()} disabled={busy || !name.trim()}>
                {busy ? 'Creating…' : `Create deck${totals?.taken ? ` (taking ${totals.taken} from other decks)` : ''}`}
              </button>
            </div>
          </div>
        )}
      </div>
    </dialog>
  )
}
