import { type ReactNode, useMemo, useState } from 'react'
import { colorClass } from '../lib/colors'
import { valueLabel } from '../lib/labels'
import type { SkillIndex } from '../lib/skills'
import type { Facet, FacetSelection, FacetState, FieldDef } from '../lib/types'
import Tooltip from './Tooltip'

const collator = new Intl.Collator('en', { numeric: true, sensitivity: 'base' })
const KEYWORD_RULES_URL = 'https://www.dbs-cardgame.com/us-en/rule/keyword-skills.php'

type Mode = 'chips' | 'list' | 'range'

interface Section {
  key: string
  mode: Mode
  open?: boolean
  sort?: 'count' | 'alpha' // por defecto alfabético
  skills?: boolean // tooltips con el texto oficial + variantes ('Over Realm X' -> 3, 4, 5…)
}

// Orden y forma de cada filtro en el panel lateral
const SECTIONS: Section[] = [
  { key: 'legality', mode: 'chips', open: true },
  { key: 'type', mode: 'chips', open: true },
  { key: 'color', mode: 'chips', open: true },
  { key: 'energy', mode: 'chips', open: true },
  { key: 'power', mode: 'range', open: true },
  { key: 'timing', mode: 'chips', open: true, skills: true },
  { key: 'keyword_skill', mode: 'list', open: true, skills: true },
  { key: 'keyword_rule', mode: 'list', open: true, skills: true },
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
  skills: SkillIndex
}

export default function FacetPanel({ fields, global, context, state, onChange, skills }: Props) {
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
      {SECTIONS.map(({ key, mode, open, sort, skills: withSkills }) => {
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
              {withSkills && (
                <a
                  className="rules-link"
                  href={KEYWORD_RULES_URL}
                  target="_blank"
                  rel="noreferrer"
                  title="Reglas oficiales de las keyword skills"
                  onClick={(e) => e.stopPropagation()}
                >
                  ⓘ
                </a>
              )}
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
              <Chips
                field={key}
                facet={facet}
                counts={counts}
                sel={sel}
                skills={withSkills ? skills : undefined}
                onChange={(s) => update(key, s)}
              />
            ) : (
              <ValueList
                facet={facet}
                counts={counts}
                sel={sel}
                sort={sort}
                onChange={(s) => update(key, s)}
                skills={withSkills ? skills : undefined}
                variants={
                  withSkills
                    ? {
                        sel: state.keyword ?? EMPTY,
                        counts: new Map(
                          (context?.keyword?.values ?? global.keyword?.values ?? []).map((v) => [String(v.value), v.count]),
                        ),
                        onChange: (s) => update('keyword', s),
                      }
                    : undefined
                }
              />
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

function SkillTip({ skills, name, children }: { skills?: SkillIndex; name: string; children: ReactNode }) {
  const skill = skills?.describe(name)
  if (!skills) return <>{children}</>
  return (
    <Tooltip
      title={`[${name}]`}
      text={skill?.description ?? 'No aparece en la página oficial de keyword skills (es posterior a su última actualización).'}
    >
      {children}
    </Tooltip>
  )
}

function Chips({ field, facet, counts, sel, onChange, skills }: ListProps & { field: string; skills?: SkillIndex }) {
  return (
    <div className="chips">
      {[...facet.values]
        .sort((a, b) => collator.compare(valueLabel(field, a.value), valueLabel(field, b.value)))
        .map(({ value }) => {
        const n = counts.get(String(value)) ?? 0
        const on = sel.values.includes(value)
        return (
          <SkillTip key={String(value)} skills={skills} name={String(value)}>
            <button
              className={`chip ${on ? 'on' : ''} ${!n && !on ? 'zero' : ''} ${colorClass(value)} ${field === 'legality' ? `lg-${value}` : ''}`}
              onClick={() => onChange(toggle(sel, value))}
              title={skills ? undefined : `${n} cartas`}
            >
              {valueLabel(field, value)} <small>{n}</small>
            </button>
          </SkillTip>
        )
      })}
    </div>
  )
}

interface VariantProps {
  sel: FacetSelection
  counts: Map<string, number>
  onChange: (s: FacetSelection) => void
}

function ValueList({
  facet,
  counts,
  sel,
  sort = 'alpha',
  onChange,
  skills,
  variants,
}: ListProps & { sort?: 'count' | 'alpha'; skills?: SkillIndex; variants?: VariantProps }) {
  const [filter, setFilter] = useState('')
  const [expanded, setExpanded] = useState(false)
  const [openVariants, setOpenVariants] = useState<Record<string, boolean>>({})
  const needle = filter.trim().toLowerCase()
  const values = facet.values.filter(({ value }) => !needle || String(value).toLowerCase().includes(needle))
  // Orden alfabético ('Burst 2' antes que 'Burst 10'); con la lista plegada se ven los 10
  // primeros y, además, los que estén marcados
  const sorted = [...values].sort((a, b) =>
    sort === 'count'
      ? (counts.get(String(b.value)) ?? 0) - (counts.get(String(a.value)) ?? 0)
      : collator.compare(String(a.value), String(b.value)),
  )
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
        {sorted.filter((v, i) => i < limit || sel.values.includes(v.value)).map(({ value }) => {
          const n = counts.get(String(value)) ?? 0
          const on = sel.values.includes(value)
          const name = String(value)
          const vars = skills && variants ? skills.variants(name) : []
          const varsOn = vars.filter((v) => variants?.sel.values.includes(v.value)).length
          const showVars = !!openVariants[name] || varsOn > 0
          return (
            <li key={name} className={!n && !on ? 'zero' : ''}>
              <div className="value-row">
                <label>
                  <input type="checkbox" checked={on} onChange={() => onChange(toggle(sel, value))} />
                  <SkillTip skills={skills} name={name}>
                    <span className="value-label">{name}</span>
                  </SkillTip>
                  <small>{n}</small>
                </label>
                {vars.length > 1 && (
                  <button
                    className={`variants-toggle ${showVars ? 'open' : ''}`}
                    onClick={() => setOpenVariants({ ...openVariants, [name]: !showVars })}
                    title="Elegir valores concretos"
                  >
                    {varsOn > 0 ? varsOn : vars.length}
                  </button>
                )}
              </div>
              {showVars && variants && (
                <ul className="variants">
                  {vars.map((v) => {
                    const vn = variants.counts.get(String(v.value)) ?? 0
                    const von = variants.sel.values.includes(v.value)
                    return (
                      <li key={String(v.value)} className={!vn && !von ? 'zero' : ''}>
                        <label>
                          <input
                            type="checkbox"
                            checked={von}
                            onChange={() => variants.onChange(toggle({ ...variants.sel, match: 'any' }, v.value))}
                          />
                          <span className="value-label">{String(v.value)}</span>
                          <small>{vn}</small>
                        </label>
                      </li>
                    )
                  })}
                </ul>
              )}
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
