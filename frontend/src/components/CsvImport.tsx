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
          text: `«${a.number}» es ambigua (${a.options.map((o) => o.card_set || o.id).join(' / ')}): añade la columna id o la edición`,
        })),
      ].sort((a, b) => a.line - b.line)
    : []

  return (
    <>
      <button className="btn backup-link" onClick={() => setOpen(true)} title="Suma a tu colección las copias de un CSV (no borra nada)">
        Importar CSV
      </button>
      {open && (
        <div className="modal-backdrop" onClick={() => !busy && close()}>
          <div className="modal csv-import" role="dialog" aria-modal="true" aria-labelledby="csv-import-title" onClick={(e) => e.stopPropagation()}>
            <button className="icon-btn close" onClick={close} disabled={busy} aria-label="Cerrar">
              ✕
            </button>
            <h2 id="csv-import-title">Importar CSV</h2>
            <p className="muted small">
              Suma las copias del fichero a tu colección; no borra ni cambia nada de lo que ya tienes. Columnas:{' '}
              <code>id</code> o <code>número</code> (y <code>edición</code> si hay varias impresiones), <code>cantidad</code>,
              y opcionales <code>ubicación</code>, <code>falsa</code> y <code>notas</code>. Vale el CSV de «Descargar CSV».
            </p>

            {applied === null && (
              <label className="csv-file">
                <input type="file" accept=".csv,text/csv" disabled={busy} onChange={(e) => pick(e.target.files?.[0])} />
                {fileName || 'Elegir fichero…'}
              </label>
            )}

            {busy && <p className="muted">Leyendo…</p>}
            {error && <p className="error">{error}</p>}

            {preview && applied === null && (
              <div className="csv-preview">
                <p>
                  <strong>{preview.totals.copies}</strong> copias en <strong>{preview.totals.rows}</strong> filas
                  {preview.totals.fakes > 0 && <> (de ellas {preview.totals.fakes} falsas)</>}.
                  {preview.totals.skipped > 0 && <> Se saltan {preview.totals.skipped} filas.</>}
                </p>
                {preview.totals.unknown_locations.length > 0 && (
                  <p className="csv-warn">
                    Estas ubicaciones no existen y sus cartas irán a «Sin ubicar»:{' '}
                    {preview.totals.unknown_locations.map((l) => `«${l}»`).join(', ')}
                  </p>
                )}
                {warnings.length > 0 && (
                  <ul className="csv-skips">
                    {warnings.slice(0, SHOWN).map((w) => (
                      <li key={`${w.line}-${w.text}`}>
                        <span className="muted">Fila {w.line}:</span> {w.text}
                      </li>
                    ))}
                    {warnings.length > SHOWN && <li className="muted">… y {warnings.length - SHOWN} más</li>}
                  </ul>
                )}
                <div className="csv-actions">
                  <button className="btn ghost" onClick={close} disabled={busy}>
                    Cancelar
                  </button>
                  <button className="btn primary" onClick={apply} disabled={busy || preview.totals.copies === 0}>
                    Sumar {preview.totals.copies} copias
                  </button>
                </div>
              </div>
            )}

            {applied !== null && (
              <div className="csv-preview">
                <p>
                  ✔ Añadidas <strong>{applied}</strong> copias a tu colección.
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
