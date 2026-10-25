import { useEffect, useMemo, useState } from 'react'
import { api } from '../lib/api'
import type {
  CardSummary, DeckChange, DeckDetail, DeckVersionDetail, LeaderRecord, Location, Match, MatchInput, MatchRecord,
  MatchResult, RestorePlan, RestoreResult, RestoreSource,
} from '../lib/types'

/** Líderes rivales que se ven en la cabecera (los demás, en «Ver más»). */
const RECENT = 5
const RESULT_LABELS: Record<MatchResult, string> = { win: 'Victoria', loss: 'Derrota', draw: 'Empate' }
const SECTION_LABELS = { main: 'Mazo', z: 'Z Deck', side: 'Side' } as const

const today = () => new Date().toISOString().slice(0, 10)
const fmtDate = (iso: string) =>
  new Date(iso.length === 10 ? `${iso}T12:00:00` : iso).toLocaleDateString('es-ES', { day: 'numeric', month: 'short', year: 'numeric' })
const pct = (r: MatchRecord) => (r.win_rate == null ? '—' : `${Math.round(r.win_rate * 100)}%`)
export const versionLabel = (v: { number: number; name: string }) => `v${v.number}${v.name ? ` · ${v.name}` : ''}`

/** Selector de versiones del mazo: la principal (lo que hay ahora) y las guardadas, con sus cambios. */
export function VersionBar({
  detail,
  selected,
  version,
  onSelect,
  onChanged,
  onRestored,
}: {
  detail: DeckDetail
  /** Versión seleccionada (null: la principal). */
  selected: number | null
  version: DeckVersionDetail | null
  onSelect: (id: number | null) => void
  onChanged: () => void
  /** Se ha hecho principal una versión: las copias se han movido. */
  onRestored: (result: RestoreResult) => void
}) {
  const [restoring, setRestoring] = useState(false)
  const [saving, setSaving] = useState(false)
  const [form, setForm] = useState<{ name: string; notes: string } | null>(null)
  const [error, setError] = useState('')
  const latest = detail.versions[0]

  const save = async () => {
    if (!form) return
    setSaving(true)
    setError('')
    try {
      await api.saveDeckVersion(detail.deck.id, form.name.trim(), form.notes.trim())
      setForm(null)
      onChanged()
    } catch (e) {
      setError((e as Error).message)
    } finally {
      setSaving(false)
    }
  }

  const rename = async () => {
    if (!version) return
    const name = window.prompt('Nombre de la versión', version.name)
    if (name == null) return
    await api.updateDeckVersion(version.id, { name: name.trim() })
    onChanged()
  }

  const remove = async () => {
    if (!version || !window.confirm(`¿Borrar ${versionLabel(version)}? La lista actual del mazo no cambia.`)) return
    try {
      await api.deleteDeckVersion(version.id)
      onSelect(null)
      onChanged()
    } catch (e) {
      window.alert((e as Error).message)
    }
  }

  return (
    <section className="deck-versions" aria-label="Versiones de la lista">
      <div className="deck-version-tabs" role="tablist">
        <button role="tab" aria-selected={selected == null} className={selected == null ? 'on' : ''} onClick={() => onSelect(null)}>
          <strong>Principal</strong>
          <small>{detail.changes.length ? 'con cambios' : latest ? `= ${`v${latest.number}`}` : 'lista actual'}</small>
        </button>
        {detail.versions.map((v) => (
          <button
            key={v.id}
            role="tab"
            aria-selected={selected === v.id}
            className={selected === v.id ? 'on' : ''}
            onClick={() => onSelect(v.id)}
            title={`${versionLabel(v)} · ${fmtDate(v.created_at)}${v.automatic ? ' · guardada al anotar una partida' : ''}`}
          >
            <strong>{versionLabel(v)}</strong>
            <small>
              {fmtDate(v.created_at)}
              {v.record.played ? ` · ${v.record.wins}-${v.record.losses}${v.record.draws ? `-${v.record.draws}` : ''}` : ''}
            </small>
          </button>
        ))}
      </div>

      {selected == null ? (
        <div className="deck-version-info">
          {detail.changes.length > 0 && latest ? (
            <ChangeList title={`Cambios desde ${versionLabel(latest)}`} changes={detail.changes} catalog={detail.catalog} />
          ) : (
            <p className="muted small">
              {latest
                ? `La lista actual es igual que ${versionLabel(latest)}.`
                : 'Aún no hay versiones guardadas. Guarda una para seguir la evolución del mazo; al anotar partidas se guarda sola si la lista ha cambiado.'}
            </p>
          )}
          {form ? (
            <div className="deck-version-form">
              <input className="input"
                autoFocus
                placeholder={`Nombre (opcional), p. ej. «Más removal»`}
                value={form.name}
                onChange={(e) => setForm({ ...form, name: e.target.value })}
                onKeyDown={(e) => e.key === 'Enter' && save()}
                maxLength={80}
              />
              <input className="input"
                placeholder="Notas (opcional)"
                value={form.notes}
                onChange={(e) => setForm({ ...form, notes: e.target.value })}
                onKeyDown={(e) => e.key === 'Enter' && save()}
              />
              <button className="btn primary" onClick={save} disabled={saving}>
                {saving ? 'Guardando…' : `Guardar v${(latest?.number ?? 0) + 1}`}
              </button>
              <button className="btn" onClick={() => setForm(null)}>Cancelar</button>
              {error && <span className="error small">{error}</span>}
            </div>
          ) : (
            <button
              className="btn primary"
              onClick={() => setForm({ name: '', notes: '' })}
              disabled={latest != null && detail.changes.length === 0}
              title={latest && detail.changes.length === 0 ? 'No hay cambios respecto a la última versión' : 'Guarda la lista actual como una versión'}
            >
              Guardar versión
            </button>
          )}
        </div>
      ) : version ? (
        <div className="deck-version-info">
          <div className="deck-version-head">
            <span>
              <strong>{versionLabel(version)}</strong> · guardada el {fmtDate(version.created_at)}
              {version.automatic && <span className="deck-tag">automática</span>}
            </span>
            <span className="deck-version-actions">
              <button
                className="btn primary small"
                onClick={() => setRestoring(true)}
                title="Mueve las copias para que el mazo tenga físicamente esta lista"
              >
                Hacer principal
              </button>
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
          unsaved={detail.changes.length > 0}
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

/** De dónde se cogerían `need` copias en automático (el orden que usa el escáner). */
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

/**
 * Hacer principal una versión. La lista principal es lo que hay físicamente en el mazo, así que
 * se enseña qué copias salen (y adónde van) y cuáles entran (y de dónde), y se mueven al confirmar.
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
  /** La lista actual tiene cambios sin guardar como versión. */
  unsaved: boolean
  onClose: () => void
  onDone: (result: RestoreResult) => void
}) {
  const [plan, setPlan] = useState<RestorePlan | null>(null)
  const [locations, setLocations] = useState<Location[]>([])
  const [target, setTarget] = useState<number | null>(null)
  const [targets, setTargets] = useState<Record<number, number>>({})
  const [sources, setSources] = useState<Record<number, number>>({})
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    Promise.all([api.restorePlan(version.id), api.locations()])
      .then(([p, locs]) => {
        setPlan(p)
        setTarget(p.default_target.id)
        setLocations(locs.filter((l) => l.id !== deckId))
      })
      .catch((e) => setError((e as Error).message))
  }, [version.id, deckId])

  const out = plan?.outgoing.reduce((n, r) => n + r.quantity, 0) ?? 0
  const inn = plan?.incoming.reduce((n, r) => n + r.quantity, 0) ?? 0
  const missing = plan?.incoming.reduce((n, r) => n + r.missing, 0) ?? 0
  const fromDecks = plan
    ? plan.incoming.flatMap((r) => {
        const chosen = r.sources.find((s) => s.id === sources[r.bandai_id])
        const ordered = chosen ? [chosen, ...r.sources.filter((s) => s !== chosen)] : r.sources
        return autoTake(ordered, r.quantity)
          .filter((t) => t.source.kind === 'deck')
          .map((t) => t.source.name)
      })
    : []
  const card = (id: number) => plan?.catalog[id]

  const run = async () => {
    if (!plan || target == null) return
    setBusy(true)
    setError('')
    try {
      onDone(await api.restoreVersion(version.id, { default_target: target, targets, sources }))
    } catch (e) {
      setError((e as Error).message)
      setBusy(false)
    }
  }

  return (
    <Modal title={`Hacer principal ${versionLabel(version)}`} onClose={onClose}>
      {!plan ? (
        error ? <p className="error">{error}</p> : <p className="muted">Calculando qué copias hay que mover…</p>
      ) : (
        <div className="restore">
          <p className="muted small">
            La lista principal es lo que tienes físicamente en el mazo. Para que pase a ser {versionLabel(version)}, se mueven
            estas copias en tu colección (haz lo mismo con las cartas de verdad).
          </p>
          {unsaved && (
            <p className="deck-check warn">
              ⚠ La lista actual tiene cambios sin guardar como versión: guárdala antes si quieres poder volver a ella.
            </p>
          )}

          {out === 0 && inn === 0 ? (
            <p>Las copias del mazo ya coinciden con {versionLabel(version)}; solo se ajusta el side deck.</p>
          ) : null}

          {out > 0 && (
            <section className="restore-block">
              <header>
                <h3>
                  Salen del mazo <span>{out} copias</span>
                </h3>
                <label className="restore-target">
                  Llevarlas a
                  <select className="input small" value={target ?? ''} onChange={(e) => setTarget(Number(e.target.value))}>
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
                      {c && <img src={c.image_url} alt="" loading="lazy" referrerPolicy="no-referrer" />}
                      <span className="restore-name">
                        <small>{c?.card_number}</small> {c?.name ?? `#${r.bandai_id}`}
                      </span>
                      <b>
                        −{r.quantity}
                        {r.fakes > 0 && <small> ({r.fakes} falsa{r.fakes > 1 ? 's' : ''})</small>}
                      </b>
                      <select
                        className="input small"
                        value={targets[r.bandai_id] ?? ''}
                        onChange={(e) =>
                          setTargets(({ [r.bandai_id]: _old, ...rest }) =>
                            e.target.value ? { ...rest, [r.bandai_id]: Number(e.target.value) } : rest,
                          )
                        }
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
                  Entran al mazo <span>{inn} copias</span>
                </h3>
              </header>
              <ul className="restore-list">
                {plan.incoming.map((r) => {
                  const c = card(r.bandai_id)
                  const auto = autoTake(r.sources, r.quantity)
                  return (
                    <li key={r.bandai_id} className={r.missing ? 'short' : ''}>
                      {c && <img src={c.image_url} alt="" loading="lazy" referrerPolicy="no-referrer" />}
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
                          value={sources[r.bandai_id] ?? ''}
                          onChange={(e) =>
                            setSources(({ [r.bandai_id]: _old, ...rest }) =>
                              e.target.value ? { ...rest, [r.bandai_id]: Number(e.target.value) } : rest,
                            )
                          }
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
              ⚠ Faltan {missing} {missing === 1 ? 'copia' : 'copias'}: el mazo quedará incompleto hasta que las consigas.
            </p>
          )}

          <div className="match-form-actions">
            {error && <span className="error small">{error}</span>}
            <button className="btn" onClick={onClose}>
              Cancelar
            </button>
            <button className="btn primary" onClick={run} disabled={busy}>
              {busy ? 'Moviendo…' : out + inn > 0 ? `Mover ${out + inn - missing} copias y hacer principal` : 'Hacer principal'}
            </button>
          </div>
        </div>
      )}
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
                {card && <img src={card.image_url} alt="" loading="lazy" referrerPolicy="no-referrer" />}
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
                        {card && <img src={card.image_url} alt="" loading="lazy" referrerPolicy="no-referrer" />}
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
                  {card ? <img src={card.image_url} alt="" loading="lazy" referrerPolicy="no-referrer" /> : <span className="match-noimg" />}
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
            {leader && <img src={leader.image_url} alt="" referrerPolicy="no-referrer" />}
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
                <img src={card.image_url} alt="" referrerPolicy="no-referrer" />
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
                <img src={c.image_url} alt="" loading="lazy" referrerPolicy="no-referrer" />
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
