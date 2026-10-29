import { useEffect, useState } from 'react'
import { api, COLLECTION_BACKUP_URL } from '../lib/api'
import type { RestorePreview } from '../lib/types'

const CONFIRM_WORD = 'replace'
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
  if (!iso) return 'unknown date'
  const d = new Date(iso)
  return Number.isNaN(d.getTime()) ? iso : d.toLocaleString('en-GB', { dateStyle: 'long', timeStyle: 'short' })
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
        throw new Error("The file isn't valid JSON. Choose the one you got with “Download backup”.")
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
        title="Replaces your collection with one from a backup made with “Download backup” (with a preview)"
      >
        Restore backup
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
            <button className="icon-btn close" onClick={close} disabled={busy} aria-label="Close">
              ✕
            </button>
            <h2 id="restore-title">Restore a backup</h2>
            <p className="muted small">
              <strong>Replaces</strong> your copies with those in a backup made with “Download backup”: anything not in
              the backup is removed. Locations are kept (missing ones are created) and decks keep their
              versions and matches. Before applying you'll see exactly what changes.
            </p>

            {applied === null && (
              <label className="csv-file">
                <input type="file" accept=".json,application/json" disabled={busy} onChange={(e) => pick(e.target.files?.[0])} />
                {fileName || 'Choose backup (.json)…'}
              </label>
            )}

            {busy && <p className="muted">{preview ? 'Restoring…' : 'Reading the backup…'}</p>}
            {error && <p className="error">{error}</p>}

            {preview && applied === null && (
              <div className="csv-preview">
                <p className="muted small">Backup from {formatDate(preview.exported_at)}.</p>
                <div className="restore-totals">
                  <div>
                    <small>Now</small>
                    <strong>{preview.before.copies.toLocaleString('en-GB')}</strong>
                    <span>copies · {preview.before.cards.toLocaleString('en-GB')} cards</span>
                  </div>
                  <span aria-hidden>→</span>
                  <div>
                    <small>After</small>
                    <strong>{preview.after.copies.toLocaleString('en-GB')}</strong>
                    <span>
                      copies · {preview.after.cards.toLocaleString('en-GB')} cards
                      {preview.after.fakes > 0 && <> · {preview.after.fakes} fakes</>}
                    </span>
                  </div>
                </div>

                {preview.changes_total === 0 ? (
                  <p>✔ Your collection already matches the backup: nothing to change.</p>
                ) : (
                  <>
                    <p>
                      <strong className="restore-plus">{preview.added}</strong> copies added and{' '}
                      <strong className="restore-minus">{preview.removed}</strong> removed, in {preview.changes_total} changes.
                    </p>
                    {preview.create_locations.length > 0 && (
                      <p className="small">
                        These locations will be created: {preview.create_locations.map((l) => `“${l}”`).join(', ')}
                      </p>
                    )}
                    {preview.emptied_locations.length > 0 && (
                      <p className="csv-warn">
                        These will be left empty (not deleted): {preview.emptied_locations.map((l) => `“${l}”`).join(', ')}
                      </p>
                    )}
                    {preview.locations.length > 0 && (
                      <table className="restore-locations">
                        <thead>
                          <tr>
                            <th>Location</th>
                            <th>Now</th>
                            <th>After</th>
                          </tr>
                        </thead>
                        <tbody>
                          {preview.locations.map((l) => (
                            <tr key={l.name}>
                              <td>
                                {l.name} {l.new && <span className="restore-new">new</span>}
                              </td>
                              <td>{l.before}</td>
                              <td>{l.after}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    )}
                    <details className="restore-changes">
                      <summary>See the changes card by card ({preview.changes_total})</summary>
                      <ul className="csv-skips">
                        {preview.changes.slice(0, SHOWN).map((c) => (
                          <li key={`${c.card_id}-${c.location}-${c.fake}`}>
                            <span className={c.after > c.before ? 'restore-plus' : 'restore-minus'}>
                              {c.after > c.before ? `+${c.after - c.before}` : `−${c.before - c.after}`}
                            </span>{' '}
                            {c.number} {c.name}
                            {c.fake && ' (fake)'} <span className="muted">· {c.location}: {c.before} → {c.after}</span>
                          </li>
                        ))}
                        {preview.changes_total > SHOWN && <li className="muted">… and {preview.changes_total - SHOWN} more</li>}
                      </ul>
                    </details>
                  </>
                )}

                {preview.skipped.length > 0 && (
                  <p className="csv-warn">
                    {preview.skipped.length} rows of the backup will be skipped:{' '}
                    {preview.skipped.slice(0, 5).map((s) => `${s.card} (${s.reason})`).join(' · ')}
                    {preview.skipped.length > 5 && ' …'}
                  </p>
                )}

                {preview.changes_total > 0 && (
                  <div className="restore-confirm">
                    <p className="small">
                      When you apply, <strong>a backup of your current collection is downloaded first</strong>, in case you want
                      to go back (restore it the same way, with this same button).
                    </p>
                    <label>
                      Type <code>{CONFIRM_WORD}</code> to confirm:
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
                    Cancel
                  </button>
                  {preview.changes_total > 0 && (
                    <button className="btn danger" onClick={apply} disabled={busy || !ready}>
                      Replace my collection
                    </button>
                  )}
                </div>
              </div>
            )}

            {applied !== null && (
              <div className="csv-preview">
                <p>
                  ✔ Collection restored: you now have <strong>{applied.toLocaleString('en-GB')}</strong> copies.
                </p>
                <p className="muted small">
                  A backup of how it was before has been downloaded: to undo this, restore it the same way.
                </p>
                <div className="csv-actions">
                  <button className="btn primary" onClick={close}>
                    Close
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
