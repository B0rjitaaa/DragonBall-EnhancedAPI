import { useMemo, useState } from 'react'
import { colorClass } from '../lib/colors'
import { valueLabel } from '../lib/labels'
import type { Facet, FacetSelection, FacetState, FieldDef } from '../lib/types'

type Mode = 'chips' | 'list' | 'range'

interface Section {
  key: string
  mode: Mode
  open?: boolean
}

// Orden y forma de cada filtro en el panel lateral
const SECTIONS: Section[] = [
  { key: 'legality', mode: 'chips', open: true },
  { key: 'type', mode: 'chips', open: true },
  { key: 'color', mode: 'chips', open: true },
  { key: 'energy', mode: 'chips', open: true },
  { key: 'power', mode: 'range', open: true },
  { key: 'keyword', mode: 'list', open: true },
  { key: 'keyword_family', mode: 'list' },
  { key: 'special_trait', mode: 'list' },
  { key: 'character', mode: 'list' },
  { key: 'rarity', mode: 'list' },
  { key: 'era', mode: 'list' },
  { key: 'series', mode: 'chips' },
  { key: 'set_code', mode: 'list' },
  { key: 'color_cost', mode: 'chips' },
  { key: 'combo_energy', mode: 'chips' },
  { key: 'combo_power', mode: 'chips' },
  { key: 'z_energy_cost', mode: 'chips' },
  { key: 'back_power', mode: 'range' },
]

const EMPTY: FacetSelection = { values: [], match: 'any' }

interface Props {
  fields: FieldDef[]
  global: Record<string, Facet>
  context: Record<string, Facet> | null
  state: FacetState
  onChange: (next: FacetState) => void
}

export default function FacetPanel({ fields, global, context, state, onChange }: Props) {
  const byKey = useMemo(() => Object.fromEntries(fields.map((f) => [f.key, f])), [fields])

  const update = (key: string, sel: FacetSelection) => {
    const next = { ...state }
    const empty = !sel.values.length && (sel.min ?? '') === '' && (sel.max ?? '') === ''
    if (empty) delete next[key]
    else next[key] = sel
    onChange(next)
  }

  return (
    <div className="facets">
      {SECTIONS.map(({ key, mode, open }) => {
        const field = byKey[key]
        const facet = global[key]
        if (!field || !facet) return null
        const sel = state[key] ?? EMPTY
        const active = sel.values.length + ((sel.min ?? '') !== '' ? 1 : 0) + ((sel.max ?? '') !== '' ? 1 : 0)
        const counts = new Map((context?.[key]?.values ?? facet.values).map((v) => [String(v.value), v.count]))
        return (
          <details key={key} className="facet" open={open || active > 0}>
            <summary>
              <span>{field.label}</span>
              {active > 0 && (
                <button
                  className="link small"
                  onClick={(e) => {
                    e.preventDefault()
                    update(key, EMPTY)
                  }}
                >
                  limpiar ({active})
                </button>
              )}
            </summary>
            {field.type === 'array' && mode !== 'range' && (
              <MatchToggle sel={sel} onChange={(s) => update(key, s)} />
            )}
            {mode === 'range' ? (
              <RangeFilter facet={facet} sel={sel} onChange={(s) => update(key, s)} />
            ) : mode === 'chips' ? (
              <Chips field={key} facet={facet} counts={counts} sel={sel} onChange={(s) => update(key, s)} />
            ) : (
              <ValueList facet={facet} counts={counts} sel={sel} onChange={(s) => update(key, s)} />
            )}
          </details>
        )
      })}
    </div>
  )
}

function toggle(sel: FacetSelection, value: string | number): FacetSelection {
  const has = sel.values.includes(value)
  return { ...sel, values: has ? sel.values.filter((v) => v !== value) : [...sel.values, value] }
}

function MatchToggle({ sel, onChange }: { sel: FacetSelection; onChange: (s: FacetSelection) => void }) {
  if (sel.values.length < 2) return null
  return (
    <div className="match-toggle" role="group" aria-label="Combinar valores">
      {(['any', 'all'] as const).map((m) => (
        <button key={m} className={sel.match === m ? 'on' : ''} onClick={() => onChange({ ...sel, match: m })}>
          {m === 'any' ? 'Cualquiera (O)' : 'Todos (Y)'}
        </button>
      ))}
    </div>
  )
}

interface ListProps {
  facet: Facet
  counts: Map<string, number>
  sel: FacetSelection
  onChange: (s: FacetSelection) => void
}

function Chips({ field, facet, counts, sel, onChange }: ListProps & { field: string }) {
  return (
    <div className="chips">
      {facet.values.map(({ value }) => {
        const n = counts.get(String(value)) ?? 0
        const on = sel.values.includes(value)
        return (
          <button
            key={String(value)}
            className={`chip ${on ? 'on' : ''} ${!n && !on ? 'zero' : ''} ${colorClass(value)} ${field === 'legality' ? `lg-${value}` : ''}`}
            onClick={() => onChange(toggle(sel, value))}
            title={`${n} cartas`}
          >
            {valueLabel(field, value)} <small>{n}</small>
          </button>
        )
      })}
    </div>
  )
}

function ValueList({ facet, counts, sel, onChange }: ListProps) {
  const [filter, setFilter] = useState('')
  const [expanded, setExpanded] = useState(false)
  const needle = filter.trim().toLowerCase()
  const values = facet.values.filter(({ value }) => !needle || String(value).toLowerCase().includes(needle))
  // Seleccionados primero, luego por recuento en la búsqueda actual
  const sorted = [...values].sort((a, b) => {
    const sa = sel.values.includes(a.value) ? 1 : 0
    const sb = sel.values.includes(b.value) ? 1 : 0
    if (sa !== sb) return sb - sa
    return (counts.get(String(b.value)) ?? 0) - (counts.get(String(a.value)) ?? 0)
  })
  const limit = expanded || needle ? 200 : 10
  return (
    <div className="value-list">
      {facet.values.length > 10 && (
        <input
          className="input small"
          placeholder={`Buscar entre ${facet.values.length}…`}
          value={filter}
          onChange={(e) => setFilter(e.target.value)}
        />
      )}
      <ul>
        {sorted.slice(0, limit).map(({ value }) => {
          const n = counts.get(String(value)) ?? 0
          const on = sel.values.includes(value)
          return (
            <li key={String(value)} className={!n && !on ? 'zero' : ''}>
              <label>
                <input type="checkbox" checked={on} onChange={() => onChange(toggle(sel, value))} />
                <span className="value-label">{String(value)}</span>
                <small>{n}</small>
              </label>
            </li>
          )
        })}
      </ul>
      {!needle && sorted.length > 10 && (
        <button className="link small" onClick={() => setExpanded(!expanded)}>
          {expanded ? 'Ver menos' : `Ver todos (${sorted.length})`}
        </button>
      )}
    </div>
  )
}

function RangeFilter({ facet, sel, onChange }: { facet: Facet; sel: FacetSelection; onChange: (s: FacetSelection) => void }) {
  const parse = (v: string): number | '' => (v === '' ? '' : Number(v))
  return (
    <div className="range">
      <input
        className="input small"
        type="number"
        placeholder={facet.min != null ? `mín ${facet.min}` : 'mín'}
        value={sel.min ?? ''}
        onChange={(e) => onChange({ ...sel, min: parse(e.target.value) })}
      />
      <span>–</span>
      <input
        className="input small"
        type="number"
        placeholder={facet.max != null ? `máx ${facet.max}` : 'máx'}
        value={sel.max ?? ''}
        onChange={(e) => onChange({ ...sel, max: parse(e.target.value) })}
      />
    </div>
  )
}
