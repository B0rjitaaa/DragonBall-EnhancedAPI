import { useEffect, useRef, useState } from 'react'
import { api } from '../lib/api'
import { formatEur } from '../lib/prices'
import { locationPath } from '../lib/query'
import PickList from './PickList'
import DeckPreviewDialog from './DeckPreviewDialog'
import { previewDeckCards } from '../lib/deckPreview'
import { KIND_LABELS } from './OwnedPanel'
import { cardThumb, groupNotes, type DeckImportPreview, type DeckImportResult, type DeckImportRow, type PickGroup } from '../lib/types'

const SECTION_LABEL: Record<string, string> = { leader: 'Leader', main: 'Main', z: 'Z', side: 'Side' }

/** Importar un mazo: pegar el enlace (DeckPlanet, Top Deck Diffusion, Time Chamber) o la lista en texto → ver qué
 * tienes libre, qué está en otros mazos (y elegir de cuáles coger) y qué falta → crear el mazo. */
export default function DeckImport({
  onClose,
  onDone,
  planned,
}: {
  onClose: () => void
  onDone: () => void
  /** Montar un mazo futuro: se salta el paso de pegar la lista y, al crear el mazo, deja de ser futuro. */
  planned?: { id: number; name: string; source: string; lines: DeckImportPreview['lines'] }
}) {
  const ref = useRef<HTMLDialogElement>(null)
  const [source, setSource] = useState('')
  const [preview, setPreview] = useState<DeckImportPreview | null>(null)
  const [name, setName] = useState('')
  const [takeFrom, setTakeFrom] = useState<Set<number>>(() => new Set())
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [result, setResult] = useState<DeckImportResult | null>(null)
  // Posiciones del archivador que se cogen, por «<ubicación>-<carta>» (por defecto, las que propone el servidor).
  const [choices, setChoices] = useState<Record<string, string[]>>({})
  // Comprobación: por sitio (dónde coger cada carta) o carta a carta (con sus secciones).
  const [view, setView] = useState<'place' | 'card'>('place')
  // «Preview deck»: ver cómo quedaría el mazo, sin crear nada.
  const [showDeck, setShowDeck] = useState(false)

  const [savedFuture, setSavedFuture] = useState(false)

  useEffect(() => {
    ref.current?.showModal()
    // Montar un mazo futuro: directamente a la comprobación, con su lista.
    if (planned) void check(planned)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const check = async (from?: typeof planned) => {
    setBusy(true)
    setError(null)
    try {
      let data = from ? await api.previewDeckImportFor(from.lines, from.source, from.name, null) : await api.previewDeckImport(source)
      // Ese Leader ya está en un mazo tuyo: por defecto, la lista se añade a ese mazo.
      if (data.existing_decks.length) {
        data = await api.previewDeckImportFor(data.lines, data.source, data.name, data.existing_decks[0].id)
      }
      setPreview(data)
      setChoices(defaultChoices(data))
      setName(from?.name || data.name)
      setTakeFrom(new Set())
    } catch (e) {
      setError((e as Error).message)
    } finally {
      setBusy(false)
    }
  }

  // Elegir a qué mazo va la lista (o crear uno nuevo): se recalcula lo que ya está, lo que entra y lo que sale.
  const chooseTarget = async (target: number | null) => {
    if (!preview) return
    setBusy(true)
    setError(null)
    try {
      const data = await api.previewDeckImportFor(preview.lines, preview.source, preview.name, target)
      setPreview(data)
      setChoices(defaultChoices(data))
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
      setResult(await api.importDeck(preview.lines, name, preview.source, [...takeFrom], preview.target?.id ?? null, choices))
      // Ya montado: deja de ser un mazo futuro.
      if (planned) await api.deletePlannedDeck(planned.id).catch(() => {})
      onDone()
    } catch (e) {
      setError((e as Error).message)
    } finally {
      setBusy(false)
    }
  }

  // Lo que falta según los mazos elegidos (las copias de los mazos no elegidos también faltan).
  // Sitios que cuentan: los libres y los mazos marcados.
  const groups = preview ? preview.by_location.filter((g) => g.kind !== 'deck' || takeFrom.has(g.location_id)) : []
  // Posiciones elegidas de más (+) o de menos (−) respecto a lo que pide la lista, por número de carta.
  const choiceDelta = new Map<string, number>()
  for (const g of groups) {
    for (const c of g.cards) {
      if (!c.options?.length) continue
      const chosen = choices[`${g.location_id}-${c.bandai_id}`]?.length ?? c.notes.length
      choiceDelta.set(c.number, (choiceDelta.get(c.number) ?? 0) + chosen - (c.needed ?? c.quantity))
    }
  }
  const missingBase = (r: DeckImportRow) => r.missing + r.in_use.filter((u) => !takeFrom.has(u.deck_id)).reduce((n, u) => n + u.quantity, 0)
  const missingNow = (r: DeckImportRow) => Math.max(0, missingBase(r) - (choiceDelta.get(r.number) ?? 0))
  const extraOf = (r: DeckImportRow) => Math.max(0, (choiceDelta.get(r.number) ?? 0) - missingBase(r))
  // Cuántas copias se cogen de una posición (puede haber varias en el mismo bolsillo: la línea sale repetida).
  const setChoice = (key: string, line: string, k: number, current: string[]) =>
    setChoices((all) => ({ ...all, [key]: [...current.filter((l) => l !== line), ...Array<string>(k).fill(line)] }))
  const totals = preview && {
    taken: preview.rows.reduce((n, r) => n + r.in_use.filter((u) => takeFrom.has(u.deck_id)).reduce((m, u) => m + u.quantity, 0), 0),
    missing: preview.rows.reduce((n, r) => n + missingNow(r), 0),
    extra: preview.rows.reduce((n, r) => n + extraOf(r), 0),
    cost: preview.rows.reduce((sum, r) => sum + missingNow(r) * (preview.catalog[r.bandai_id]?.price?.eur ?? 0), 0),
  }

  // Las cartas del mazo tal como quedaría: Leader, Main y Z juntos (la vista los separa por tipo) y el side aparte.
  // Las que faltan (según lo elegido ahora) se apuntan primero en el side, igual que al crear el mazo.
  const deckCards = () => previewDeckCards(preview, missingNow)

  const toggle = (deckId: number) =>
    setTakeFrom((s) => {
      const next = new Set(s)
      if (next.has(deckId)) next.delete(deckId)
      else next.add(deckId)
      return next
    })

  return (
    <dialog
      ref={ref}
      className="loc-dialog deck-import"
      onClose={(e) => e.target === e.currentTarget && onClose()}
      onCancel={(e) => busy && e.target === e.currentTarget && e.preventDefault()}
    >
      <div className="deck-import-body">
        <header className="deck-import-head">
          <h2>{planned ? `Build “${planned.name}”` : 'Import a deck'}</h2>
          <button type="button" className="icon-btn" onClick={() => ref.current?.close()} disabled={busy} aria-label="Close">
            ✕
          </button>
        </header>

        {result ? (
          <div className="deck-import-done">
            <p>
              ✔{' '}
              {result.created ? (
                <>
                  <strong>“{result.deck.name}”</strong> is ready
                </>
              ) : (
                <>
                  <strong>“{result.deck.name}”</strong> has a new main list (v{result.version})
                </>
              )}
              : <strong>{result.moved}</strong> copies moved into it
              {result.removed > 0 && (
                <>
                  , <strong>{result.removed}</strong> moved out to “Unsorted”
                </>
              )}
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
            {preview.existing_decks.length > 0 && (
              <fieldset className="deck-import-target" disabled={busy}>
                <legend>You already have a deck with this Leader</legend>
                {preview.existing_decks.map((d) => (
                  <label key={d.id} className={preview.target?.id === d.id ? 'on' : ''}>
                    <input type="radio" name="import-target" checked={preview.target?.id === d.id} onChange={() => void chooseTarget(d.id)} />
                    <span>
                      <span>
                        Add it as a <strong>new list</strong> of <strong>“{d.name}”</strong>
                      </span>
                      <small>It becomes the main list; cards that aren't in it go to “Unsorted”. Older lists stay in its history.</small>
                    </span>
                  </label>
                ))}
                <label className={preview.target == null ? 'on' : ''}>
                  <input type="radio" name="import-target" checked={preview.target == null} onChange={() => void chooseTarget(null)} />
                  <span>Create a new deck</span>
                </label>
              </fieldset>
            )}
            {preview.target == null && (
              <label>
                Deck name
                <input className="input" value={name} maxLength={80} onChange={(e) => setName(e.target.value)} placeholder="e.g. Goku Black" />
              </label>
            )}

            <div className="deck-import-totals">
              {preview.target && (
                <span className="in">
                  <strong>{preview.totals.in_deck}</strong> already in the deck
                </span>
              )}
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
              {!!totals?.extra && (
                <span className="in">
                  <strong>+{totals.extra}</strong> extra (positions you picked)
                </span>
              )}
              {preview.totals.leaving > 0 && (
                <span className="out">
                  <strong>{preview.totals.leaving}</strong> leave the deck
                </span>
              )}
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

            {preview.target && preview.leaving.length > 0 && (
              <div className="deck-import-leaving">
                <strong>
                  ↩ {preview.totals.leaving} {preview.totals.leaving === 1 ? 'copy leaves' : 'copies leave'} “{preview.target.name}”
                </strong>
                <p className="small muted">They aren't in the new list: they move to “Unsorted” so you can put them away later.</p>
                <ul className="deck-import-leaving-list">
                  {preview.leaving.map((c) => (
                    <li key={`${c.bandai_id}-${c.fake}`}>
                      {c.quantity}× {c.name} <span className="muted">({c.number}{c.fake ? ', fake' : ''})</span>
                    </li>
                  ))}
                </ul>
              </div>
            )}

            <div className="deck-import-view" role="group" aria-label="View">
              <button type="button" className={view === 'place' ? 'on' : ''} onClick={() => setView('place')} aria-pressed={view === 'place'}>
                By place
              </button>
              <button type="button" className={view === 'card' ? 'on' : ''} onClick={() => setView('card')} aria-pressed={view === 'card'}>
                By card
              </button>
            </div>

            {view === 'place' && (
              <ByPlace
                groups={groups}
                choices={choices}
                onSet={setChoice}
                inDeck={preview.target ? preview.rows.filter((r) => r.in_deck > 0) : []}
                deckName={preview.target?.name}
                missing={preview.rows.filter((r) => missingNow(r) > 0).map((r) => ({ row: r, n: missingNow(r) }))}
                catalog={preview.catalog}
              />
            )}

            {view === 'card' && <ul className="deck-import-rows">
              {preview.rows.map((r) => {
                const card = preview.catalog[r.bandai_id]
                const missing = missingNow(r)
                const taken = r.in_use.filter((u) => takeFrom.has(u.deck_id)).reduce((n, u) => n + u.quantity, 0)
                const blocked = r.in_use.filter((u) => !takeFrom.has(u.deck_id))
                return (
                  <li key={r.number} className={missing ? 'miss' : taken ? 'use' : r.free ? 'ok' : 'in'}>
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
                      {r.in_deck > 0 && <span className="in">■ {r.in_deck} already in the deck</span>}
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
            </ul>}

            {(preview.unknown.length > 0 || preview.unread.length > 0) && (
              <p className="csv-warn small">
                {preview.unknown.length > 0 && <>Not in the catalog (skipped): {preview.unknown.join(', ')}. </>}
                {preview.unread.length > 0 && <>Lines not understood: {preview.unread.slice(0, 5).join(' · ')}</>}
              </p>
            )}
            {error && <p className="error">{error}</p>}
            <div className="loc-dialog-actions">
              <button type="button" className="btn ghost" onClick={() => (planned ? ref.current?.close() : setPreview(null))} disabled={busy}>
                {planned ? 'Cancel' : '← Back'}
              </button>
              <span className="spacer" />
              {!planned && (
                <button
                  type="button"
                  className="btn"
                  disabled={busy || savedFuture}
                  title="Keep this list in Locations → Future decks, to build it later"
                  onClick={() => {
                    setBusy(true)
                    api
                      .createPlannedDeck({ lines: preview.lines, source: preview.source, name: name.trim() || preview.name })
                      .then(() => {
                        setSavedFuture(true)
                        onDone()
                      })
                      .catch((e: Error) => setError(e.message))
                      .finally(() => setBusy(false))
                  }}
                >
                  {savedFuture ? '✓ Saved in Future decks' : '☆ Save as future deck'}
                </button>
              )}
              <button
                type="button"
                className="btn"
                onClick={() => setShowDeck(true)}
                disabled={busy}
                title="See how the deck would look, without creating anything"
              >
                👁 Preview deck
              </button>
              <button
                type="button"
                className="btn primary"
                onClick={() => void create()}
                disabled={busy || (preview.target == null && !name.trim())}
              >
                {busy
                  ? 'Saving…'
                  : `${preview.target ? `Add the list to “${preview.target.name}”` : 'Create deck'}${totals?.taken ? ` (taking ${totals.taken} from other decks)` : ''}`}
              </button>
            </div>
          </div>
        )}
      </div>
      {showDeck && preview && (
        <DeckPreviewDialog
          name={preview.target?.name ?? (name.trim() || preview.name)}
          {...deckCards()}
          note={
            preview.target
              ? `This is the list you'd add to “${preview.target.name}”. Nothing has been saved yet.`
              : 'Nothing has been created yet: close this to go back to the import.'
          }
          onClose={() => setShowDeck(false)}
        />
      )}
    </dialog>
  )
}

/** La comprobación por sitio: un bloque por Binder / caja / mazo con las cartas que hay que coger de ahí (en su
 *  orden y con su posición) y, al final, lo que ya está en el mazo y lo que falta. */
function ByPlace({
  groups, choices, onSet, inDeck, deckName, missing, catalog,
}: {
  groups: PickGroup[]
  choices: Record<string, string[]>
  onSet: (key: string, line: string, k: number, current: string[]) => void
  inDeck: DeckImportRow[]
  deckName?: string
  missing: { row: DeckImportRow; n: number }[]
  catalog: DeckImportPreview['catalog']
}) {
  type Item = {
    id: number; qty: number; name: string; sub: string; where?: string[]
    /** Archivador: posiciones que se pueden marcar (la clave de la elección y las marcadas). */
    pick?: { key: string; options: string[]; chosen: string[] }
  }
  const block = (key: string, title: string, label: string, tone: string, items: Item[]) => (
    <section key={key} className={`place-group ${tone}`}>
      <h4>
        {title} <small>{label}</small>
        <span className="place-count">{items.reduce((n, i) => n + i.qty, 0)}</span>
      </h4>
      <ul>
        {items.map((i) => (
          <li key={`${key}-${i.id}-${i.sub}`}>
            {catalog[i.id] ? <img src={cardThumb(catalog[i.id])} alt="" loading="lazy" referrerPolicy="no-referrer" /> : <span />}
            <span className="pick-card">
              <strong>
                {i.qty}× {i.name}
              </strong>
              <small>{i.sub}</small>
            </span>
            {i.pick ? (
              <span className="pick-where">
                {i.where?.filter((w) => w.startsWith('#')).map((w) => (
                  <span key={w} className="pick-pos">{w}</span>
                ))}
                {[...new Set(i.pick.options)].map((line) => {
                  const { key, options, chosen } = i.pick!
                  const have = options.filter((l) => l === line).length
                  const k = chosen.filter((l) => l === line).length
                  if (have === 1) {
                    const on = k > 0
                    return (
                      <button
                        key={line}
                        type="button"
                        className={`pick-option ${on ? 'on' : ''}`}
                        aria-pressed={on}
                        title={on ? 'Taking this copy (tap to leave it in the binder)' : 'Tap to take this copy too'}
                        onClick={() => onSet(key, line, on ? 0 : 1, chosen)}
                      >
                        {on ? '✓ ' : ''}{line}
                      </button>
                    )
                  }
                  // Varias copias en el mismo bolsillo: cuántas se cogen.
                  return (
                    <span key={line} className={`pick-option stacked ${k ? 'on' : ''}`} title={`${have} copies in this pocket`}>
                      <button type="button" onClick={() => onSet(key, line, k - 1, chosen)} disabled={k === 0} aria-label={`Take one copy less from ${line}`}>
                        −
                      </button>
                      {k ? '✓ ' : ''}{line} · <strong>{k}/{have}</strong>
                      <button type="button" onClick={() => onSet(key, line, k + 1, chosen)} disabled={k >= have} aria-label={`Take one more copy from ${line}`}>
                        +
                      </button>
                    </span>
                  )
                })}
              </span>
            ) : i.where && i.where.length > 0 && (
              <span className="pick-where">
                {i.where.map((w) => (
                  <span key={w} className={w.startsWith('#') ? 'pick-pos' : 'pick-note'}>
                    {w}
                  </span>
                ))}
              </span>
            )}
          </li>
        ))}
      </ul>
    </section>
  )
  return (
    <div className="place-groups">
      {groups.map((g) =>
        block(
          `g${g.location_id}`,
          g.location,
          g.kind === 'deck' ? 'from this deck' : (KIND_LABELS[g.kind] ?? g.kind),
          g.kind === 'deck' ? 'use' : 'ok',
          g.cards.map((c) => {
            const key = `${g.location_id}-${c.bandai_id}`
            const chosen = choices[key] ?? c.notes
            const multi = (c.options?.length ?? 0) > 0
            return {
              id: c.bandai_id, qty: multi ? chosen.length : c.quantity, name: c.name,
              sub: `${c.number}${c.rarity ? ` · ${c.rarity}` : ''}${multi && chosen.length !== c.needed ? ` · the list needs ${c.needed}` : ''}`,
              where: [...(c.position ? [`#${c.position}`] : []), ...(multi ? [] : groupNotes(c.notes))],
              pick: multi ? { key, options: c.options!, chosen } : undefined,
            }
          }),
        ),
      )}
      {inDeck.length > 0 &&
        block('in', `Already in “${deckName}”`, 'stays in the deck', 'in', inDeck.map((r) => ({ id: r.bandai_id, qty: r.in_deck, name: r.name, sub: r.number })))}
      {missing.length > 0 &&
        block('miss', 'Missing', "you don't have them", 'miss', missing.map(({ row, n }) => ({
          id: row.bandai_id, qty: n, name: row.name,
          sub: `${row.number}${catalog[row.bandai_id]?.price ? ` · ≈ ${formatEur((catalog[row.bandai_id]?.price?.eur ?? 0) * n)}` : ''}`,
        })))}
      {groups.length === 0 && inDeck.length === 0 && missing.length === 0 && <p className="muted small">Nothing to fetch.</p>}
    </div>
  )
}

/** Posiciones del archivador que se cogen por defecto (las que propone el servidor). */
function defaultChoices(data: DeckImportPreview): Record<string, string[]> {
  const out: Record<string, string[]> = {}
  for (const g of data.by_location) for (const c of g.cards) if (c.options?.length) out[`${g.location_id}-${c.bandai_id}`] = c.notes
  return out
}
