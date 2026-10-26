import { useEffect, useMemo, useState } from 'react'
import { api } from '../lib/api'
import type {
  CardSummary, DeckChange, DeckDetail, DeckListCard, DeckVersionDetail, LeaderRecord, Location, Match, MatchInput,
  MatchRecord, MatchResult, RestorePlan, RestoreResult, RestoreSource,
} from '../lib/types'
import { cardThumb } from '../lib/types'

/** Líderes rivales que se ven en la cabecera (los demás, en «Ver más»). */
const RECENT = 5
const RESULT_LABELS: Record<MatchResult, string> = { win: 'Victoria', loss: 'Derrota', draw: 'Empate' }
const SECTION_LABELS = { main: 'Mazo', z: 'Z Deck', side: 'Side' } as const

const today = () => new Date().toISOString().slice(0, 10)
const fmtDate = (iso: string) =>
  new Date(iso.length === 10 ? `${iso}T12:00:00` : iso).toLocaleDateString('es-ES', { day: 'numeric', month: 'short', year: 'numeric' })
const pct = (r: MatchRecord) => (r.win_rate == null ? '—' : `${Math.round(r.win_rate * 100)}%`)
export const versionLabel = (v: { number: number; name: string }) => `v${v.number}${v.name ? ` · ${v.name}` : ''}`

/** Selector de listas del mazo: la principal (lo que hay en la caja, editable) y las guardadas. */
export function VersionBar({
  detail,
  selected,
  version,
  onSelect,
  onChanged,
  onRestored,
  draftChanges,
  catalog,
  onSaveList,
  onDiscard,
}: {
  detail: DeckDetail
  /** Lista seleccionada (null: la principal). */
  selected: number | null
  version: DeckVersionDetail | null
  onSelect: (id: number | null) => void
  onChanged: () => void
  /** Se ha hecho principal una lista: las copias se han movido. */
  onRestored: (result: RestoreResult) => void
  /** Lo editado en la lista principal y aún sin guardar. */
  draftChanges: DeckChange[]
  catalog: Record<number, CardSummary>
  onSaveList: () => void
  onDiscard: () => void
}) {
  const [restoring, setRestoring] = useState(false)
  const principal = detail.versions.find((v) => v.principal) ?? null
  const boxChanged = detail.changes.length > 0

  const rename = async () => {
    if (!version) return
    const name = window.prompt('Nombre de la lista', version.name)
    if (name == null) return
    await api.updateDeckVersion(version.id, { name: name.trim() })
    onChanged()
  }

  const remove = async () => {
    if (!version || !window.confirm(`¿Borrar ${versionLabel(version)}? Las cartas de la caja no se mueven.`)) return
    try {
      await api.deleteDeckVersion(version.id)
      onSelect(null)
      onChanged()
    } catch (e) {
      window.alert((e as Error).message)
    }
  }

  return (
    <section className="deck-versions" aria-label="Listas del mazo">
      <div className="deck-version-tabs" role="tablist">
        <button role="tab" aria-selected={selected == null} className={selected == null ? 'on' : ''} onClick={() => onSelect(null)}>
          <strong>Principal</strong>
          <small>
            {draftChanges.length ? 'editando' : boxChanged ? 'la caja ha cambiado' : principal ? `★ ${versionLabel(principal)}` : 'lo que hay en la caja'}
          </small>
        </button>
        {detail.versions.map((v) => (
          <button
            key={v.id}
            role="tab"
            aria-selected={selected === v.id}
            className={`${selected === v.id ? 'on' : ''} ${v.principal ? 'principal' : ''}`}
            onClick={() => onSelect(v.id)}
            title={`${versionLabel(v)} · ${fmtDate(v.created_at)}${v.principal ? ' · lista principal' : ''}${v.automatic ? ' · guardada al anotar una partida' : ''}`}
          >
            <strong>
              {v.principal && '★ '}
              {versionLabel(v)}
            </strong>
            <small>
              {fmtDate(v.created_at)}
              {v.record.played ? ` · ${v.record.wins}-${v.record.losses}${v.record.draws ? `-${v.record.draws}` : ''}` : ''}
            </small>
          </button>
        ))}
      </div>

      {selected == null ? (
        <div className="deck-version-info">
          {draftChanges.length > 0 ? (
            <ChangeList title="Cambios sin guardar" changes={draftChanges} catalog={catalog} />
          ) : boxChanged && principal ? (
            <ChangeList
              title={`La caja no coincide con la principal (${versionLabel(principal)})`}
              changes={detail.changes}
              catalog={detail.catalog}
            />
          ) : (
            <p className="muted small">
              {principal
                ? `En la caja está la lista principal, ${versionLabel(principal)}. Usa − / + en las cartas o «Añadir carta» para preparar una lista nueva.`
                : detail.versions.length
                  ? 'Ninguna lista es la principal todavía: guarda la de la caja (pasará a serlo) o elige una lista guardada y pulsa «Hacer principal».'
                  : 'Aún no hay listas guardadas: guarda la de la caja (o edítala antes con − / + y «Añadir carta»). Al guardarla pasa a ser la principal.'}
            </p>
          )}
          <span className="deck-version-actions">
            {draftChanges.length > 0 && (
              <button className="btn" onClick={() => window.confirm('¿Descartar los cambios de la lista?') && onDiscard()}>
                Descartar
              </button>
            )}
            <button
              className="btn primary"
              onClick={onSaveList}
              disabled={!draftChanges.length && !boxChanged && principal != null}
              title={
                !draftChanges.length && !boxChanged && principal
                  ? 'No hay cambios respecto a la lista principal'
                  : 'Guarda esta lista como una lista nueva del mazo'
              }
            >
              Guardar lista
            </button>
          </span>
        </div>
      ) : version ? (
        <div className="deck-version-info">
          <div className="deck-version-head">
            <span>
              <strong>{versionLabel(version)}</strong> · guardada el {fmtDate(version.created_at)}
              {version.principal && <span className="deck-tag principal">★ principal</span>}
              {version.automatic && <span className="deck-tag">automática</span>}
            </span>
            <span className="deck-version-actions">
              {(!version.principal || boxChanged) && (
                <button
                  className="btn primary small"
                  onClick={() => setRestoring(true)}
                  title="Mueve las copias para que la caja del mazo tenga esta lista; las partidas se anotarán con ella"
                >
                  {version.principal ? 'Recolocar la caja' : 'Hacer principal'}
                </button>
              )}
              <button className="link small" onClick={rename}>
                Renombrar
              </button>
              {version.matches.length === 0 && (
                <button className="link small danger" onClick={remove}>
                  Borrar
                </button>
              )}
            </span>
          </div>
          {version.notes && <p className="small">{version.notes}</p>}
          {version.previous != null ? (
            version.changes.length ? (
              <ChangeList title={`Cambios desde v${version.previous}`} changes={version.changes} catalog={version.catalog} />
            ) : (
              <p className="muted small">Misma lista que v{version.previous}.</p>
            )
          ) : (
            <p className="muted small">Primera versión del mazo.</p>
          )}
        </div>
      ) : (
        <p className="muted small">Cargando versión…</p>
      )}
      {restoring && version && (
        <RestoreModal
          deckId={detail.deck.id}
          version={version}
          unsaved={boxChanged || draftChanges.length > 0}
          onClose={() => setRestoring(false)}
          onDone={(result) => {
            setRestoring(false)
            onRestored(result)
          }}
        />
      )}
    </section>
  )
}

const sourceLabel = (s: RestoreSource) =>
  `${s.name} (${s.authentic + s.fakes}${s.fakes ? `, ${s.fakes} falsa${s.fakes > 1 ? 's' : ''}` : ''})${s.kind === 'deck' ? ' · otro mazo' : ''}`

/** De dónde se cogerían `need` copias en automático (el mismo orden que usa el servidor). */
function autoTake(sources: RestoreSource[], need: number): { source: RestoreSource; n: number }[] {
  const out = []
  for (const s of sources) {
    const n = Math.min(need, s.authentic + s.fakes)
    if (n) out.push({ source: s, n })
    need -= n
    if (!need) break
  }
  return out
}

interface PlanChoices {
  target: number | null
  targets: Record<number, number>
  sources: Record<number, number>
}

/** Plan de movimientos de copias (para hacer principal una lista) y lo que elige el usuario. */
function usePlan(deckId: number, load: () => Promise<RestorePlan>, key: string) {
  const [plan, setPlan] = useState<RestorePlan | null>(null)
  const [locations, setLocations] = useState<Location[]>([])
  const [choices, setChoices] = useState<PlanChoices>({ target: null, targets: {}, sources: {} })
  const [error, setError] = useState('')
  useEffect(() => {
    Promise.all([load(), api.locations()])
      .then(([p, locs]) => {
        setPlan(p)
        setChoices((c) => ({ ...c, target: c.target ?? p.default_target.id }))
        setLocations(locs.filter((l) => l.id !== deckId))
      })
      .catch((e) => setError((e as Error).message))
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [deckId, key])
  const out = plan?.outgoing.reduce((n, r) => n + r.quantity, 0) ?? 0
  const inn = plan?.incoming.reduce((n, r) => n + r.quantity, 0) ?? 0
  const missing = plan?.incoming.reduce((n, r) => n + r.missing, 0) ?? 0
  const body = () => ({ default_target: choices.target!, targets: choices.targets, sources: choices.sources })
  return { plan, locations, choices, setChoices, error, out, inn, missing, moves: out + inn - missing, body }
}

/** Qué copias salen de la caja (y adónde) y cuáles entran (y de dónde), con avisos. */
function PlanEditor({ p }: { p: ReturnType<typeof usePlan> }) {
  const { plan, locations, choices, setChoices, out, inn, missing } = p
  if (!plan) return null
  const card = (id: number) => plan.catalog[id]
  const pick = (key: 'targets' | 'sources', id: number, value: string) =>
    setChoices((c) => {
      const { [id]: _old, ...rest } = c[key]
      void _old
      return { ...c, [key]: value ? { ...rest, [id]: Number(value) } : rest }
    })
  const fromDecks = plan.incoming.flatMap((r) => {
    const chosen = r.sources.find((s) => s.id === choices.sources[r.bandai_id])
    const ordered = chosen ? [chosen, ...r.sources.filter((s) => s !== chosen)] : r.sources
    return autoTake(ordered, r.quantity)
      .filter((t) => t.source.kind === 'deck')
      .map((t) => t.source.name)
  })
  return (
    <>
      {out > 0 && (
        <section className="restore-block">
          <header>
            <h3>
              Salen de la caja <span>{out} copias</span>
            </h3>
            <label className="restore-target">
              Llevarlas a
              <select
                className="input small"
                value={choices.target ?? ''}
                onChange={(e) => setChoices((c) => ({ ...c, target: Number(e.target.value) }))}
              >
                {locations.map((l) => (
                  <option key={l.id} value={l.id}>
                    {l.name}
                  </option>
                ))}
              </select>
            </label>
          </header>
          <ul className="restore-list">
            {plan.outgoing.map((r) => {
              const c = card(r.bandai_id)
              return (
                <li key={r.bandai_id}>
                  {c && <img src={cardThumb(c)} alt="" loading="lazy" referrerPolicy="no-referrer" />}
                  <span className="restore-name">
                    <small>{c?.card_number}</small> {c?.name ?? `#${r.bandai_id}`}
                  </span>
                  <b>
                    −{r.quantity}
                    {r.fakes > 0 && <small> ({r.fakes} falsa{r.fakes > 1 ? 's' : ''})</small>}
                  </b>
                  <select
                    className="input small"
                    value={choices.targets[r.bandai_id] ?? ''}
                    onChange={(e) => pick('targets', r.bandai_id, e.target.value)}
                    aria-label={`Adónde van las copias de ${c?.name ?? r.bandai_id}`}
                  >
                    <option value="">Con el resto</option>
                    {locations.map((l) => (
                      <option key={l.id} value={l.id}>
                        {l.name}
                      </option>
                    ))}
                  </select>
                </li>
              )
            })}
          </ul>
        </section>
      )}

      {inn > 0 && (
        <section className="restore-block">
          <header>
            <h3>
              Entran en la caja <span>{inn} copias</span>
            </h3>
          </header>
          <ul className="restore-list">
            {plan.incoming.map((r) => {
              const c = card(r.bandai_id)
              const auto = autoTake(r.sources, r.quantity)
              return (
                <li key={r.bandai_id} className={r.missing ? 'short' : ''}>
                  {c && <img src={cardThumb(c)} alt="" loading="lazy" referrerPolicy="no-referrer" />}
                  <span className="restore-name">
                    <small>{c?.card_number}</small> {c?.name ?? `#${r.bandai_id}`}
                    {r.missing > 0 && (
                      <em>
                        {r.missing === r.quantity ? 'No tienes' : `Te faltan ${r.missing}`}: no {r.missing === 1 ? 'está' : 'están'}{' '}
                        en ninguna otra ubicación
                      </em>
                    )}
                  </span>
                  <b>+{r.quantity}</b>
                  {r.sources.length > 0 ? (
                    <select
                      className="input small"
                      value={choices.sources[r.bandai_id] ?? ''}
                      onChange={(e) => pick('sources', r.bandai_id, e.target.value)}
                      aria-label={`De dónde se cogen las copias de ${c?.name ?? r.bandai_id}`}
                    >
                      <option value="">De: {auto.map((t) => `${t.source.name} ${t.n}`).join(' + ')}</option>
                      {r.sources.map((s) => (
                        <option key={s.id} value={s.id}>
                          Primero de {sourceLabel(s)}
                        </option>
                      ))}
                    </select>
                  ) : (
                    <span className="muted small">—</span>
                  )}
                </li>
              )
            })}
          </ul>
        </section>
      )}

      {fromDecks.length > 0 && (
        <p className="deck-check warn">⚠ Se sacarán copias de otros mazos: {[...new Set(fromDecks)].join(', ')}.</p>
      )}
      {missing > 0 && (
        <p className="deck-check error">
          ⚠ Faltan {missing} {missing === 1 ? 'copia' : 'copias'}: la caja quedará incompleta hasta que las consigas.
        </p>
      )}
    </>
  )
}

/**
 * Hacer principal una lista guardada. La principal es la que está físicamente en la caja del mazo,
 * así que se enseña qué copias salen (y adónde van) y cuáles entran (y de dónde), y se mueven al confirmar.
 */
function RestoreModal({
  deckId,
  version,
  unsaved,
  onClose,
  onDone,
}: {
  deckId: number
  version: DeckVersionDetail
  /** Lo que hay en la caja (o lo editado) no está guardado como lista. */
  unsaved: boolean
  onClose: () => void
  onDone: (result: RestoreResult) => void
}) {
  const p = usePlan(deckId, () => api.restorePlan(version.id), String(version.id))
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')

  const run = async () => {
    setBusy(true)
    setError('')
    try {
      onDone(await api.restoreVersion(version.id, p.body()))
    } catch (e) {
      setError((e as Error).message)
      setBusy(false)
    }
  }

  return (
    <Modal title={`Hacer principal ${versionLabel(version)}`} onClose={onClose}>
      {!p.plan ? (
        p.error ? <p className="error">{p.error}</p> : <p className="muted">Calculando qué copias hay que mover…</p>
      ) : (
        <div className="restore">
          <p className="muted small">
            La lista principal es la que está físicamente en la caja del mazo y con la que se anotan las partidas. Para que
            pase a ser {versionLabel(version)}, se mueven estas copias en tu colección (haz lo mismo con las cartas de verdad).
          </p>
          {unsaved && (
            <p className="deck-check warn">
              ⚠ Lo que hay ahora en la caja no está guardado como lista: guárdalo antes si quieres poder volver a ello.
            </p>
          )}
          {p.out === 0 && p.inn === 0 && <p>La caja ya tiene estas copias; solo se ajusta el side deck.</p>}
          <PlanEditor p={p} />
          <div className="match-form-actions">
            {error && <span className="error small">{error}</span>}
            <button className="btn" onClick={onClose}>
              Cancelar
            </button>
            <button className="btn primary" onClick={run} disabled={busy}>
              {busy ? 'Moviendo…' : p.moves > 0 ? `Mover ${p.moves} copias y hacer principal` : 'Hacer principal'}
            </button>
          </div>
        </div>
      )}
    </Modal>
  )
}

/** Guardar la lista editada como lista nueva; si no está en la caja, avisa de lo que habría que mover. */
export function SaveListModal({
  deckId,
  nextNumber,
  cards,
  onClose,
  onSaved,
}: {
  deckId: number
  nextNumber: number
  cards: DeckListCard[]
  onClose: () => void
  /** `result`: si además se ha hecho principal (copias movidas). */
  onSaved: (result: RestoreResult | null) => void
}) {
  const key = JSON.stringify(cards)
  const p = usePlan(deckId, () => api.deckPlan(deckId, cards), key)
  const [name, setName] = useState('')
  const [notes, setNotes] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const inBox = p.plan != null && p.out === 0 && p.inn === 0

  const save = async (principal: boolean) => {
    setBusy(true)
    setError('')
    try {
      const v = await api.saveDeckVersion(deckId, name.trim(), notes.trim(), cards)
      // Si coincide con la caja ya es la principal; si solo cambia el side, se coloca igualmente.
      onSaved(principal && !v.principal ? await api.restoreVersion(v.id, p.body()) : null)
    } catch (e) {
      setError((e as Error).message)
      setBusy(false)
    }
  }

  return (
    <Modal title={`Guardar lista v${nextNumber}`} onClose={onClose}>
      <div className="restore">
        <div className="save-list-fields">
          <label>
            <span className="match-label">Nombre</span>
            <input
              className="input"
              autoFocus
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="Opcional, p. ej. «Más removal»"
              maxLength={80}
            />
          </label>
          <label>
            <span className="match-label">Notas</span>
            <input className="input" value={notes} onChange={(e) => setNotes(e.target.value)} placeholder="Opcional" />
          </label>
        </div>
        {!p.plan ? (
          p.error ? <p className="error">{p.error}</p> : <p className="muted">Comprobando qué hay en la caja…</p>
        ) : inBox ? (
          <p className="deck-check ok">✓ Estas cartas ya están en la caja del mazo: la lista pasará a ser la principal.</p>
        ) : (
          <>
            <p className="small">
              Para que sea la <strong>lista principal</strong> (la de la caja, con la que se anotan las partidas) habría que mover
              estas copias. Puedes guardarla sin moverlas y hacerla principal más adelante.
            </p>
            <PlanEditor p={p} />
          </>
        )}
        <div className="match-form-actions">
          {error && <span className="error small">{error}</span>}
          <button className="btn" onClick={onClose}>
            Cancelar
          </button>
          {p.plan && !inBox && (
            <button className="btn" onClick={() => save(false)} disabled={busy}>
              Solo guardar
            </button>
          )}
          <button className="btn primary" onClick={() => save(true)} disabled={busy || !p.plan}>
            {busy ? 'Guardando…' : inBox ? 'Guardar lista' : `Guardar y hacer principal (${p.moves} copias)`}
          </button>
        </div>
      </div>
    </Modal>
  )
}

/** Buscar una carta en todo el catálogo para añadirla a la lista. */
export function CardPicker({
  onPick,
  quantityOf,
  onClose,
}: {
  onPick: (card: CardSummary) => void
  /** Copias que ya hay de esa carta en la lista. */
  quantityOf: (id: number) => number
  onClose: () => void
}) {
  const [q, setQ] = useState('')
  const [results, setResults] = useState<CardSummary[]>([])
  const [loading, setLoading] = useState(false)
  const [, rerender] = useState(0)

  useEffect(() => {
    const text = q.trim()
    if (text.length < 2) {
      setResults([])
      return
    }
    const ctrl = new AbortController()
    const t = window.setTimeout(() => {
      setLoading(true)
      api
        .search({ q: text, page_size: 30, ordering: 'number' }, ctrl.signal)
        .then((r) => setResults(r.results))
        .catch(() => {})
        .finally(() => setLoading(false))
    }, 250)
    return () => {
      ctrl.abort()
      window.clearTimeout(t)
    }
  }, [q])

  return (
    <Modal title="Añadir carta a la lista" onClose={onClose}>
      <div className="card-picker">
        <input
          className="input"
          autoFocus
          value={q}
          onChange={(e) => setQ(e.target.value)}
          placeholder="Nombre, número (BT1-030) o texto de la carta…"
        />
        <p className="muted small">
          Pulsa una carta para sumar una copia (puedes pulsar varias veces). Se añade al borrador: nada se mueve hasta que
          guardes la lista y la hagas principal.
        </p>
        {q.trim().length >= 2 && !loading && results.length === 0 && <p className="muted">Ninguna carta coincide.</p>}
        <ul className="card-picker-grid">
          {results.map((c) => {
            const n = quantityOf(c.id)
            return (
              <li key={c.id}>
                <button
                  onClick={() => {
                    onPick(c)
                    rerender((x) => x + 1)
                  }}
                  title={`${c.card_number} · ${c.name} · ${c.card_set}`}
                >
                  <img src={cardThumb(c)} alt={c.name} loading="lazy" referrerPolicy="no-referrer" />
                  {n > 0 && <span className="deck-qty">{n}</span>}
                  <span className="deck-card-name">
                    <small>{c.card_number}</small>
                    {c.name}
                  </span>
                </button>
              </li>
            )
          })}
        </ul>
        <div className="match-form-actions">
          <button className="btn primary" onClick={onClose}>
            Listo
          </button>
        </div>
      </div>
    </Modal>
  )
}

/** Cartas añadidas y quitadas entre dos listas. */
function ChangeList({ title, changes, catalog }: { title: string; changes: DeckChange[]; catalog: Record<number, CardSummary> }) {
  const added = changes.filter((c) => c.delta > 0).reduce((n, c) => n + c.delta, 0)
  const removed = changes.filter((c) => c.delta < 0).reduce((n, c) => n - c.delta, 0)
  return (
    <details className="deck-changes" open={changes.length <= 6}>
      <summary>
        {title}: <span className="plus">+{added}</span> <span className="minus">−{removed}</span>
      </summary>
      <ul>
        {[...changes]
          .sort((a, b) => b.delta - a.delta)
          .map((c) => {
            const card = catalog[c.bandai_id]
            return (
              <li key={`${c.bandai_id}-${c.section}`} className={c.delta > 0 ? 'plus' : 'minus'}>
                <b>{c.delta > 0 ? `+${c.delta}` : `−${-c.delta}`}</b>
                {card && <img src={cardThumb(card)} alt="" loading="lazy" referrerPolicy="no-referrer" />}
                <span>
                  <small>{card?.card_number}</small> {card?.name ?? `#${c.bandai_id}`}
                </span>
                {c.section !== 'main' && <span className="deck-tag">{SECTION_LABELS[c.section]}</span>}
              </li>
            )
          })}
      </ul>
    </details>
  )
}

/** Partidas del mazo (o de una versión), en la cabecera: balance, por líder rival y las últimas. */
export function MatchesPanel({
  deckId,
  matches,
  record,
  byLeader,
  catalog,
  version,
  onChanged,
}: {
  deckId: number
  matches: Match[]
  record: MatchRecord
  byLeader: LeaderRecord[]
  catalog: Record<number, CardSummary>
  /** Versión seleccionada: las partidas nuevas se anotan con ella. */
  version: DeckVersionDetail | null
  onChanged: () => void
}) {
  const [editing, setEditing] = useState<Match | 'new' | null>(null)
  const [known, setKnown] = useState<Record<number, CardSummary>>({})
  const allCards = { ...catalog, ...known }
  const opponents = useMemo(() => [...new Set(matches.map((m) => m.opponent_name).filter(Boolean))], [matches])
  const events = useMemo(() => [...new Set(matches.map((m) => m.event).filter(Boolean))], [matches])
  const leaderCard = (id: number | null) => (id != null ? allCards[id] : undefined)
  const [showAll, setShowAll] = useState(false)
  // Los líderes rivales, una vez cada uno, del enfrentamiento más reciente al más antiguo.
  const recentLeaders = useMemo(() => {
    const key = (id: number | null, name: string) => `${id}-${name}`
    const order = [...new Set(matches.map((m) => key(m.opponent_leader_bandai_id, m.opponent_leader_name)))]
    return [...byLeader].sort(
      (a, b) => order.indexOf(key(a.leader_bandai_id, a.leader_name)) - order.indexOf(key(b.leader_bandai_id, b.leader_name)),
    )
  }, [matches, byLeader])

  const submit = async (input: MatchInput, leader: CardSummary | null) => {
    if (leader) setKnown((k) => ({ ...k, [leader.id]: leader }))
    if (editing && editing !== 'new') await api.updateMatch(editing.id, input)
    else await api.addMatch(deckId, version ? { ...input, version: version.id } : input)
    setEditing(null)
    onChanged()
  }

  const remove = async (m: Match) => {
    if (!window.confirm('¿Borrar esta partida?')) return
    await api.deleteMatch(m.id)
    onChanged()
  }

  return (
    <section className="deck-record" aria-label="Partidas">
      <div className="deck-record-head">
        <p className="deck-mix-title">Partidas{version ? ` con v${version.number}` : ''}</p>
        <button className="btn primary small" onClick={() => setEditing('new')}>
          + Resultado
        </button>
      </div>

      {record.played === 0 ? (
        <p className="muted small">
          Sin partidas anotadas{version ? ' con esta versión' : ''}. Pulsa «+ Resultado» al terminar una.
        </p>
      ) : (
        <>
          <div className="match-summary">
            <div className="match-rate">
              <strong>{pct(record)}</strong>
              <small>{record.played === 1 ? '1 partida' : `${record.played} partidas`}</small>
            </div>
            <div className="match-wld" aria-label="Victorias, derrotas y empates">
              <span className="win">{record.wins} V</span>
              <span className="loss">{record.losses} D</span>
              {record.draws > 0 && <span className="draw">{record.draws} E</span>}
              <div className="match-bar">
                <i className="win" style={{ flexGrow: record.wins }} />
                <i className="draw" style={{ flexGrow: record.draws }} />
                <i className="loss" style={{ flexGrow: record.losses }} />
              </div>
            </div>
          </div>

          <table className="match-leaders">
            <thead>
              <tr>
                <th>Contra</th>
                <th>V-D-E</th>
                <th>%</th>
              </tr>
            </thead>
            <tbody>
              {recentLeaders.slice(0, RECENT).map((r) => {
                const card = leaderCard(r.leader_bandai_id)
                return (
                  <tr key={`${r.leader_bandai_id}-${r.leader_name}`}>
                    <td>
                      <span className="match-leader">
                        {card && <img src={cardThumb(card)} alt="" loading="lazy" referrerPolicy="no-referrer" />}
                        <span>
                          {r.leader_name || 'Sin indicar'}
                          {card && <small>{card.card_number}</small>}
                        </span>
                      </span>
                    </td>
                    <td>
                      {r.wins}-{r.losses}-{r.draws}
                    </td>
                    <td className={r.win_rate != null && r.win_rate >= 0.5 ? 'good' : 'bad'}>{pct(r)}</td>
                  </tr>
                )
              })}
            </tbody>
          </table>

          <button className="link small deck-record-more" onClick={() => setShowAll(true)}>
            Ver todas las partidas ({record.played}) →
          </button>
        </>
      )}

      {showAll && (
        <Modal title={`Partidas${version ? ` con ${versionLabel(version)}` : ''} · ${record.wins}-${record.losses}-${record.draws}`} onClose={() => setShowAll(false)}>
          <ul className="match-list" aria-label="Todas las partidas">
            {matches.map((m) => {
              const card = leaderCard(m.opponent_leader_bandai_id)
              const details = [
                m.opponent_name,
                m.score,
                m.went_first == null ? '' : m.went_first ? 'empecé yo' : 'empezó el rival',
                m.event,
              ].filter(Boolean)
              return (
                <li key={m.id} className={`match ${m.result}`}>
                  <span className={`match-result ${m.result}`} aria-label={RESULT_LABELS[m.result]}>
                    {RESULT_LABELS[m.result][0]}
                  </span>
                  {card ? <img src={cardThumb(card)} alt="" loading="lazy" referrerPolicy="no-referrer" /> : <span className="match-noimg" />}
                  <span className="match-main">
                    <strong>vs {m.opponent_leader_name || 'líder sin indicar'}</strong>
                    <small>
                      {fmtDate(m.played_on)}
                      {m.version_number != null && ` · v${m.version_number}`}
                      {details.length > 0 && ` · ${details.join(' · ')}`}
                    </small>
                    {m.notes && <small className="match-notes">{m.notes}</small>}
                  </span>
                  <span className="match-actions">
                    <button
                      className="icon-btn"
                      onClick={() => {
                        setShowAll(false)
                        setEditing(m)
                      }}
                      title="Editar"
                      aria-label="Editar partida"
                    >
                      ✎
                    </button>
                    <button className="icon-btn" onClick={() => remove(m)} title="Borrar" aria-label="Borrar partida">
                      🗑
                    </button>
                  </span>
                </li>
              )
            })}
          </ul>
        </Modal>
      )}

      {editing && (
        <Modal title={editing === 'new' ? 'Anotar resultado' : 'Editar partida'} onClose={() => setEditing(null)}>
          <MatchForm
            initial={editing === 'new' ? null : editing}
            catalog={allCards}
            recentLeaders={byLeader}
            opponents={opponents}
            events={events}
            note={
              editing !== 'new'
                ? undefined
                : version
                  ? `Se anotará con ${versionLabel(version)}.`
                  : 'Se anotará con la lista principal (si ha cambiado desde la última versión, se guarda una versión nueva).'
            }
            onSubmit={submit}
            onCancel={() => setEditing(null)}
          />
        </Modal>
      )}
    </section>
  )
}

function Modal({ title, onClose, children }: { title: string; onClose: () => void; children: React.ReactNode }) {
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => e.key === 'Escape' && onClose()
    window.addEventListener('keydown', onKey)
    document.body.classList.add('no-scroll')
    return () => {
      window.removeEventListener('keydown', onKey)
      document.body.classList.remove('no-scroll')
    }
  }, [onClose])
  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal match-modal" role="dialog" aria-modal="true" aria-label={title} onClick={(e) => e.stopPropagation()}>
        <button className="icon-btn close" onClick={onClose} aria-label="Cerrar">
          ✕
        </button>
        <h2>{title}</h2>
        {children}
      </div>
    </div>
  )
}

function MatchForm({
  initial,
  catalog,
  recentLeaders,
  opponents,
  events,
  note,
  onSubmit,
  onCancel,
}: {
  initial: Match | null
  catalog: Record<number, CardSummary>
  recentLeaders: LeaderRecord[]
  opponents: string[]
  events: string[]
  note?: string
  onSubmit: (m: MatchInput, leader: CardSummary | null) => Promise<void>
  onCancel: () => void
}) {
  const [m, setM] = useState<MatchInput>(
    initial ?? {
      played_on: today(),
      opponent_leader_bandai_id: null,
      opponent_leader_name: '',
      opponent_name: '',
      result: 'win',
      went_first: null,
      score: '',
      event: '',
      notes: '',
    },
  )
  const [leader, setLeader] = useState<CardSummary | null>(
    initial?.opponent_leader_bandai_id != null ? (catalog[initial.opponent_leader_bandai_id] ?? null) : null,
  )
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const set = (changes: Partial<MatchInput>) => setM((prev) => ({ ...prev, ...changes }))

  const pick = (card: CardSummary | null, name = '') => {
    setLeader(card)
    set({ opponent_leader_bandai_id: card?.id ?? null, opponent_leader_name: card?.name ?? name })
  }

  const submit = async (e: React.FormEvent) => {
    e.preventDefault()
    setBusy(true)
    setError('')
    try {
      await onSubmit({ ...m, opponent_name: m.opponent_name.trim(), score: m.score.trim(), event: m.event.trim() }, leader)
    } catch (err) {
      setError((err as Error).message)
      setBusy(false)
    }
  }

  return (
    <form className="match-form" onSubmit={submit}>
      <div className="match-form-leader">
        <span className="match-label">Líder rival</span>
        {m.opponent_leader_name ? (
          <span className="match-picked">
            {leader && <img src={cardThumb(leader)} alt="" referrerPolicy="no-referrer" />}
            <span>
              <strong>{m.opponent_leader_name}</strong>
              {leader && <small>{leader.card_number}</small>}
            </span>
            <button type="button" className="link small" onClick={() => pick(null)}>
              Cambiar
            </button>
          </span>
        ) : (
          <LeaderPicker recent={recentLeaders} catalog={catalog} onPick={pick} />
        )}
      </div>

      <label>
        <span className="match-label">Resultado</span>
        <span className="seg">
          {(Object.keys(RESULT_LABELS) as MatchResult[]).map((r) => (
            <button type="button" key={r} className={`${m.result === r ? 'on' : ''} ${r}`} onClick={() => set({ result: r })}>
              {RESULT_LABELS[r]}
            </button>
          ))}
        </span>
      </label>
      <label>
        <span className="match-label">Fecha</span>
        <input className="input" type="date" value={m.played_on} max={today()} onChange={(e) => set({ played_on: e.target.value })} required />
      </label>
      <label>
        <span className="match-label">Oponente</span>
        <input className="input" list="match-opponents" value={m.opponent_name} onChange={(e) => set({ opponent_name: e.target.value })} placeholder="Nombre del jugador" />
        <datalist id="match-opponents">
          {opponents.map((o) => (
            <option key={o} value={o} />
          ))}
        </datalist>
      </label>
      <label>
        <span className="match-label">¿Quién empezó?</span>
        <span className="seg">
          {([
            [true, 'Yo'],
            [false, 'El rival'],
            [null, '—'],
          ] as const).map(([v, label]) => (
            <button type="button" key={label} className={m.went_first === v ? 'on' : ''} onClick={() => set({ went_first: v })}>
              {label}
            </button>
          ))}
        </span>
      </label>
      <label>
        <span className="match-label">Marcador</span>
        <input className="input" value={m.score} onChange={(e) => set({ score: e.target.value })} placeholder="p. ej. 2-1" maxLength={20} />
      </label>
      <label>
        <span className="match-label">Evento</span>
        <input className="input" list="match-events" value={m.event} onChange={(e) => set({ event: e.target.value })} placeholder="Torneo, tienda, casual…" />
        <datalist id="match-events">
          {events.map((o) => (
            <option key={o} value={o} />
          ))}
        </datalist>
      </label>
      <label className="match-form-notes">
        <span className="match-label">Notas</span>
        <textarea className="input" value={m.notes} onChange={(e) => set({ notes: e.target.value })} rows={2} placeholder="Qué funcionó, qué faltó…" />
      </label>

      <div className="match-form-actions">
        {note && <span className="muted small">{note}</span>}
        {error && <span className="error small">{error}</span>}
        <button type="button" className="btn" onClick={onCancel}>
          Cancelar
        </button>
        <button className="btn primary" type="submit" disabled={busy}>
          {busy ? 'Guardando…' : initial ? 'Guardar cambios' : 'Anotar partida'}
        </button>
      </div>
    </form>
  )
}

/** Buscador de cartas Líder del catálogo (o un nombre libre si no está). */
function LeaderPicker({
  recent,
  catalog,
  onPick,
}: {
  recent: LeaderRecord[]
  catalog: Record<number, CardSummary>
  onPick: (card: CardSummary | null, name?: string) => void
}) {
  const [q, setQ] = useState('')
  const [results, setResults] = useState<CardSummary[]>([])
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    const text = q.trim()
    if (text.length < 2) {
      setResults([])
      return
    }
    const ctrl = new AbortController()
    const t = window.setTimeout(() => {
      setLoading(true)
      api
        .search(
          { q: text, query: { op: 'and', children: [{ field: 'type', operator: 'eq', value: 'LEADER' }] }, page_size: 20 },
          ctrl.signal,
        )
        .then((r) => setResults(r.results.filter((c, i, all) => all.findIndex((o) => o.card_number === c.card_number) === i)))
        .catch(() => {})
        .finally(() => setLoading(false))
    }, 250)
    return () => {
      ctrl.abort()
      window.clearTimeout(t)
    }
  }, [q])

  const quick = recent.filter((r) => r.leader_bandai_id != null && catalog[r.leader_bandai_id]).slice(0, 6)

  return (
    <div className="leader-picker">
      <input className="input" autoFocus value={q} onChange={(e) => setQ(e.target.value)} placeholder="Busca el líder: nombre o número (BT1-001)…" />
      {quick.length > 0 && !q && (
        <div className="leader-quick">
          {quick.map((r) => {
            const card = catalog[r.leader_bandai_id!]
            return (
              <button type="button" key={card.id} onClick={() => onPick(card)} title={`${card.card_number} · ${card.name}`}>
                <img src={cardThumb(card)} alt="" referrerPolicy="no-referrer" />
                <span>{card.name}</span>
              </button>
            )
          })}
        </div>
      )}
      {q.trim().length >= 2 && (
        <ul className="leader-results">
          {results.map((c) => (
            <li key={c.id}>
              <button type="button" onClick={() => onPick(c)}>
                <img src={cardThumb(c)} alt="" loading="lazy" referrerPolicy="no-referrer" />
                <span>
                  <strong>{c.name}</strong>
                  <small>
                    {c.card_number} · {c.colors.join('/')}
                  </small>
                </span>
              </button>
            </li>
          ))}
          {!loading && (
            <li>
              <button type="button" className="leader-free" onClick={() => onPick(null, q.trim())}>
                Usar «{q.trim()}» sin carta
              </button>
            </li>
          )}
        </ul>
      )}
    </div>
  )
}
