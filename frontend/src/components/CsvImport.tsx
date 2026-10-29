import { useEffect, useState } from 'react'
import { api } from '../lib/api'
import type { CsvImportPreview } from '../lib/types'

const SHOWN = 20 // filas con aviso que se listan antes de resumir el resto

interface Props {
  /** Tras importar: recargar resultados y totales por ubicación. */
  onDone: () => void
}

/** Importar Mi colección desde un CSV: elegir fichero → vista previa → sumar copias (nunca borra). */
export default function CsvImport({ onDone }: Props) {
  const [open, setOpen] = useState(false)
  const [text, setText] = useState<string | null>(null)
  const [fileName, setFileName] = useState('')
  const [preview, setPreview] = useState<CsvImportPreview | null>(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [applied, setApplied] = useState<number | null>(null)

  const close = () => {
    setOpen(false)
    setText(null)
    setFileName('')
    setPreview(null)
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
    setApplied(null)
    setFileName(file.name)
    setBusy(true)
    try {
      const content = await file.text()
      setText(content)
      setPreview(await api.previewCsvImport(content))
    } catch (e) {
      setError((e as Error).message)
    } finally {
      setBusy(false)
    }
  }

  const apply = async () => {
    if (!text) return
    setBusy(true)
    setError(null)
    try {
      const result = await api.applyCsvImport(text)
      setApplied(result.applied.copies)
      onDone()
    } catch (e) {
      setError((e as Error).message)
    } finally {
      setBusy(false)
    }
  }

  const warnings = preview
    ? [
        ...preview.errors.map((e) => ({ line: e.line, text: e.reason })),
        ...preview.ambiguous.map((a) => ({
          line: a.line,
          text: `“${a.number}” is ambiguous (${a.options.map((o) => o.card_set || o.id).join(' / ')}): add the id or set column`,
        })),
      ].sort((a, b) => a.line - b.line)
    : []

  return (
    <>
      <button className="btn backup-link" onClick={() => setOpen(true)} title="Adds the copies in a CSV to your collection (doesn't delete anything)">
        Import CSV
      </button>
      {open && (
        <div className="modal-backdrop" onClick={() => !busy && close()}>
          <div className="modal csv-import" role="dialog" aria-modal="true" aria-labelledby="csv-import-title" onClick={(e) => e.stopPropagation()}>
            <button className="icon-btn close" onClick={close} disabled={busy} aria-label="Close">
              ✕
            </button>
            <h2 id="csv-import-title">Import CSV</h2>
            <p className="muted small">
              Adds the file's copies to your collection; it doesn't delete or change anything you already have. Columns:{' '}
              <code>id</code> or <code>number</code> (plus <code>set</code> if there are several printings), <code>quantity</code>,
              and optionally <code>location</code>, <code>fake</code> and <code>notes</code>. The file from “Download CSV” works.
            </p>

            {applied === null && (
              <label className="csv-file">
                <input type="file" accept=".csv,text/csv" disabled={busy} onChange={(e) => pick(e.target.files?.[0])} />
                {fileName || 'Choose file…'}
              </label>
            )}

            {busy && <p className="muted">Reading…</p>}
            {error && <p className="error">{error}</p>}

            {preview && applied === null && (
              <div className="csv-preview">
                <p>
                  <strong>{preview.totals.copies}</strong> copies in <strong>{preview.totals.rows}</strong> rows
                  {preview.totals.fakes > 0 && <> ({preview.totals.fakes} of them fake)</>}.
                  {preview.totals.skipped > 0 && <> {preview.totals.skipped} rows will be skipped.</>}
                </p>
                {preview.totals.unknown_locations.length > 0 && (
                  <p className="csv-warn">
                    These locations don't exist, so their cards will go to “Unsorted”:{' '}
                    {preview.totals.unknown_locations.map((l) => `“${l}”`).join(', ')}
                  </p>
                )}
                {warnings.length > 0 && (
                  <ul className="csv-skips">
                    {warnings.slice(0, SHOWN).map((w) => (
                      <li key={`${w.line}-${w.text}`}>
                        <span className="muted">Row {w.line}:</span> {w.text}
                      </li>
                    ))}
                    {warnings.length > SHOWN && <li className="muted">… and {warnings.length - SHOWN} more</li>}
                  </ul>
                )}
                <div className="csv-actions">
                  <button className="btn ghost" onClick={close} disabled={busy}>
                    Cancel
                  </button>
                  <button className="btn primary" onClick={apply} disabled={busy || preview.totals.copies === 0}>
                    Add {preview.totals.copies} copies
                  </button>
                </div>
              </div>
            )}

            {applied !== null && (
              <div className="csv-preview">
                <p>
                  ✔ Added <strong>{applied}</strong> copies to your collection.
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
