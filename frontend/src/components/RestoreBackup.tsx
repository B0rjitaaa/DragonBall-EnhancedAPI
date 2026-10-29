import { useEffect, useState } from 'react'
import { api, COLLECTION_BACKUP_URL } from '../lib/api'
import type { RestorePreview } from '../lib/types'

const CONFIRM_WORD = 'sustituir'
const SHOWN = 60 // cambios carta a carta que se listan antes de resumir el resto

interface Props {
  /** Tras restaurar: recargar resultados y totales por ubicación. */
  onDone: () => void
}

/** Descarga ahora la copia de la colección actual (para poder deshacer la restauración). */
function downloadCurrentBackup() {
  const a = document.createElement('a')
  a.href = COLLECTION_BACKUP_URL
  a.download = ''
  document.body.appendChild(a)
  a.click()
  a.remove()
}

function formatDate(iso: string | null): string {
  if (!iso) return 'fecha desconocida'
  const d = new Date(iso)
  return Number.isNaN(d.getTime()) ? iso : d.toLocaleString('es-ES', { dateStyle: 'long', timeStyle: 'short' })
}

/** Restaurar la copia JSON de «Descargar copia»: elegir fichero → vista previa → confirmar escribiendo
 * «sustituir» → se descarga antes una copia de lo actual → se sustituye la colección. */
export default function RestoreBackup({ onDone }: Props) {
  const [open, setOpen] = useState(false)
  const [doc, setDoc] = useState<unknown>(null)
  const [fileName, setFileName] = useState('')
  const [preview, setPreview] = useState<RestorePreview | null>(null)
  const [confirm, setConfirm] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [applied, setApplied] = useState<number | null>(null)

  const close = () => {
    setOpen(false)
    setDoc(null)
    setFileName('')
    setPreview(null)
    setConfirm('')
    setError(null)
    setApplied(null)
  }

  useEffect(() => {
    if (!open) return
    const onKey = (e: KeyboardEvent) => e.key === 'Escape' && !busy && close()
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [open, busy])

  const pick = async (file: File | undefined) => {
    if (!file) return
    setError(null)
    setPreview(null)
    setConfirm('')
    setFileName(file.name)
    setBusy(true)
    try {
      let parsed: unknown
      try {
        parsed = JSON.parse(await file.text())
      } catch {
        throw new Error('El fichero no es un JSON válido. Elige el que descargaste con «Descargar copia».')
      }
      setDoc(parsed)
      setPreview(await api.previewRestore(parsed))
    } catch (e) {
      setError((e as Error).message)
    } finally {
      setBusy(false)
    }
  }

  const apply = async () => {
    if (!doc || confirm.trim().toLowerCase() !== CONFIRM_WORD) return
    // En el mismo clic (si no, el navegador lo bloquea): la copia de lo que hay ahora, para poder deshacer.
    downloadCurrentBackup()
    setBusy(true)
    setError(null)
    try {
      const result = await api.applyRestore(doc)
      setApplied(result.applied.copies)
      onDone()
    } catch (e) {
      setError((e as Error).message)
    } finally {
      setBusy(false)
    }
  }

  const ready = confirm.trim().toLowerCase() === CONFIRM_WORD

  return (
    <>
      <button
        className="btn backup-link"
        onClick={() => setOpen(true)}
        title="Sustituye tu colección por la de una copia descargada con «Descargar copia» (con vista previa)"
      >
        Restaurar copia
      </button>
      {open && (
        <div className="modal-backdrop" onClick={() => !busy && close()}>
          <div
            className="modal csv-import restore-backup"
            role="dialog"
            aria-modal="true"
            aria-labelledby="restore-title"
            onClick={(e) => e.stopPropagation()}
          >
            <button className="icon-btn close" onClick={close} disabled={busy} aria-label="Cerrar">
              ✕
            </button>
            <h2 id="restore-title">Restaurar una copia</h2>
            <p className="muted small">
              <strong>Sustituye</strong> tus copias por las de una copia descargada con «Descargar copia»: lo que no esté
              en la copia se quita. Las ubicaciones se conservan (las que falten se crean) y los mazos mantienen sus
              versiones y partidas. Antes de aplicar verás exactamente qué cambia.
            </p>

            {applied === null && (
              <label className="csv-file">
                <input type="file" accept=".json,application/json" disabled={busy} onChange={(e) => pick(e.target.files?.[0])} />
                {fileName || 'Elegir copia (.json)…'}
              </label>
            )}

            {busy && <p className="muted">{preview ? 'Restaurando…' : 'Leyendo la copia…'}</p>}
            {error && <p className="error">{error}</p>}

            {preview && applied === null && (
              <div className="csv-preview">
                <p className="muted small">Copia del {formatDate(preview.exported_at)}.</p>
                <div className="restore-totals">
                  <div>
                    <small>Ahora</small>
                    <strong>{preview.before.copies.toLocaleString('es-ES')}</strong>
                    <span>copias · {preview.before.cards.toLocaleString('es-ES')} cartas</span>
                  </div>
                  <span aria-hidden>→</span>
                  <div>
                    <small>Después</small>
                    <strong>{preview.after.copies.toLocaleString('es-ES')}</strong>
                    <span>
                      copias · {preview.after.cards.toLocaleString('es-ES')} cartas
                      {preview.after.fakes > 0 && <> · {preview.after.fakes} falsas</>}
                    </span>
                  </div>
                </div>

                {preview.changes_total === 0 ? (
                  <p>✔ Tu colección ya es igual que la copia: no hay nada que cambiar.</p>
                ) : (
                  <>
                    <p>
                      Se añaden <strong className="restore-plus">{preview.added}</strong> copias y se quitan{' '}
                      <strong className="restore-minus">{preview.removed}</strong>, en {preview.changes_total} cambios.
                    </p>
                    {preview.create_locations.length > 0 && (
                      <p className="small">
                        Se crean estas ubicaciones: {preview.create_locations.map((l) => `«${l}»`).join(', ')}
                      </p>
                    )}
                    {preview.emptied_locations.length > 0 && (
                      <p className="csv-warn">
                        Se quedan vacías (no se borran): {preview.emptied_locations.map((l) => `«${l}»`).join(', ')}
                      </p>
                    )}
                    {preview.locations.length > 0 && (
                      <table className="restore-locations">
                        <thead>
                          <tr>
                            <th>Ubicación</th>
                            <th>Ahora</th>
                            <th>Después</th>
                          </tr>
                        </thead>
                        <tbody>
                          {preview.locations.map((l) => (
                            <tr key={l.name}>
                              <td>
                                {l.name} {l.new && <span className="restore-new">nueva</span>}
                              </td>
                              <td>{l.before}</td>
                              <td>{l.after}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    )}
                    <details className="restore-changes">
                      <summary>Ver los cambios carta a carta ({preview.changes_total})</summary>
                      <ul className="csv-skips">
                        {preview.changes.slice(0, SHOWN).map((c) => (
                          <li key={`${c.card_id}-${c.location}-${c.fake}`}>
                            <span className={c.after > c.before ? 'restore-plus' : 'restore-minus'}>
                              {c.after > c.before ? `+${c.after - c.before}` : `−${c.before - c.after}`}
                            </span>{' '}
                            {c.number} {c.name}
                            {c.fake && ' (falsa)'} <span className="muted">· {c.location}: {c.before} → {c.after}</span>
                          </li>
                        ))}
                        {preview.changes_total > SHOWN && <li className="muted">… y {preview.changes_total - SHOWN} más</li>}
                      </ul>
                    </details>
                  </>
                )}

                {preview.skipped.length > 0 && (
                  <p className="csv-warn">
                    Se saltan {preview.skipped.length} filas de la copia:{' '}
                    {preview.skipped.slice(0, 5).map((s) => `${s.card} (${s.reason})`).join(' · ')}
                    {preview.skipped.length > 5 && ' …'}
                  </p>
                )}

                {preview.changes_total > 0 && (
                  <div className="restore-confirm">
                    <p className="small">
                      Al aplicar, primero <strong>se descarga una copia de tu colección actual</strong>, por si quieres
                      volver atrás (se restaura igual, con este mismo botón).
                    </p>
                    <label>
                      Escribe <code>{CONFIRM_WORD}</code> para confirmar:
                      <input
                        className="input"
                        value={confirm}
                        onChange={(e) => setConfirm(e.target.value)}
                        placeholder={CONFIRM_WORD}
                        autoComplete="off"
                        disabled={busy}
                      />
                    </label>
                  </div>
                )}
                <div className="csv-actions">
                  <button className="btn ghost" onClick={close} disabled={busy}>
                    Cancelar
                  </button>
                  {preview.changes_total > 0 && (
                    <button className="btn danger" onClick={apply} disabled={busy || !ready}>
                      Sustituir mi colección
                    </button>
                  )}
                </div>
              </div>
            )}

            {applied !== null && (
              <div className="csv-preview">
                <p>
                  ✔ Colección restaurada: ahora tienes <strong>{applied.toLocaleString('es-ES')}</strong> copias.
                </p>
                <p className="muted small">
                  La copia de cómo estaba antes se ha descargado: si quieres deshacerlo, restáurala igual.
                </p>
                <div className="csv-actions">
                  <button className="btn primary" onClick={close}>
                    Cerrar
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </>
  )
}
