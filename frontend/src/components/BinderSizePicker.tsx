import { useState } from 'react'
import { BINDER_MAX_SIDE, BINDER_PRESETS, binderLabel, clampSide, isPreset, type BinderSize } from '../lib/binder'

/** Bolsillos por página de un archivador: los tamaños habituales o filas × columnas a mano. */
export default function BinderSizePicker({ value, onChange }: { value: BinderSize; onChange: (size: BinderSize) => void }) {
  const [custom, setCustom] = useState(!isPreset(value))
  return (
    <div className="binder-size">
      <div className="binder-size-options" role="radiogroup" aria-label="Pockets per page">
        {BINDER_PRESETS.map((p) => {
          const on = !custom && p.rows === value.rows && p.cols === value.cols
          return (
            <button
              key={`${p.rows}x${p.cols}`}
              type="button"
              role="radio"
              aria-checked={on}
              className={`binder-size-option ${on ? 'on' : ''}`}
              onClick={() => {
                setCustom(false)
                onChange(p)
              }}
            >
              <MiniGrid size={p} />
              <span>{binderLabel(p, false)}</span>
              <small>{p.rows * p.cols} pockets</small>
            </button>
          )
        })}
        <button
          type="button"
          role="radio"
          aria-checked={custom}
          className={`binder-size-option ${custom ? 'on' : ''}`}
          onClick={() => setCustom(true)}
        >
          <span className="binder-size-custom-icon" aria-hidden>
            ✎
          </span>
          <span>Custom</span>
          <small>rows × columns</small>
        </button>
      </div>
      {custom && (
        <div className="binder-size-custom">
          <label>
            Rows
            <input
              className="input"
              type="number"
              min={1}
              max={BINDER_MAX_SIDE}
              value={value.rows}
              onChange={(e) => onChange({ ...value, rows: clampSide(Number(e.target.value)) })}
            />
          </label>
          <span aria-hidden>×</span>
          <label>
            Columns
            <input
              className="input"
              type="number"
              min={1}
              max={BINDER_MAX_SIDE}
              value={value.cols}
              onChange={(e) => onChange({ ...value, cols: clampSide(Number(e.target.value)) })}
            />
          </label>
          <small className="muted">
            {value.rows * value.cols} pockets per page (up to {BINDER_MAX_SIDE} × {BINDER_MAX_SIDE})
          </small>
        </div>
      )}
    </div>
  )
}

/** Dibujo de la página: un cuadradito por bolsillo. */
function MiniGrid({ size }: { size: BinderSize }) {
  return (
    <span className="binder-mini" style={{ gridTemplateColumns: `repeat(${size.cols}, 1fr)` }} aria-hidden>
      {Array.from({ length: size.rows * size.cols }, (_, i) => (
        <i key={i} />
      ))}
    </span>
  )
}
