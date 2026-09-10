import { useId, useMemo, useState } from 'react'
import { defaultValue, newCondition, newGroup, OPERATOR_LABELS, updateNode } from '../lib/query'
import type { Condition, Facet, FieldDef, Group, QueryNode } from '../lib/types'
import { isGroup } from '../lib/types'

interface Ctx {
  fields: FieldDef[]
  byKey: Record<string, FieldDef>
  facets: Record<string, Facet>
  update: (id: string, fn: (n: QueryNode) => QueryNode | null) => void
}

interface Props {
  tree: Group
  fields: FieldDef[]
  facets: Record<string, Facet>
  onChange: (tree: Group) => void
}

export default function QueryBuilder({ tree, fields, facets, onChange }: Props) {
  const byKey = useMemo(() => Object.fromEntries(fields.map((f) => [f.key, f])), [fields])
  const ctx: Ctx = { fields, byKey, facets, update: (id, fn) => onChange(updateNode(tree, id, fn)) }
  return (
    <div className="query-builder">
      <GroupEditor group={tree} ctx={ctx} root />
    </div>
  )
}

function GroupEditor({ group, ctx, root = false }: { group: Group; ctx: Ctx; root?: boolean }) {
  const defaultField = ctx.byKey.keyword ?? ctx.fields[0]
  const add = (node: QueryNode) =>
    ctx.update(group.id, (g) => ({ ...(g as Group), children: [...(g as Group).children, node] }))

  return (
    <div className={`qb-group ${group.op} ${group.not ? 'negated' : ''} ${root ? 'root' : ''}`}>
      <div className="qb-group-head">
        <button
          className={`not-toggle ${group.not ? 'on' : ''}`}
          onClick={() => ctx.update(group.id, (g) => ({ ...g, not: !(g as Group).not }))}
          title="Negar el grupo completo"
        >
          NO
        </button>
        <div className="seg" role="group" aria-label="Operador del grupo">
          {(['and', 'or'] as const).map((op) => (
            <button
              key={op}
              className={group.op === op ? 'on' : ''}
              onClick={() => ctx.update(group.id, (g) => ({ ...g, op }))}
            >
              {op === 'and' ? 'Y (todas)' : 'O (alguna)'}
            </button>
          ))}
        </div>
        <span className="spacer" />
        <button className="btn ghost small" onClick={() => add(newCondition(defaultField))}>
          + Condición
        </button>
        <button className="btn ghost small" onClick={() => add(newGroup(group.op === 'and' ? 'or' : 'and'))}>
          + Grupo
        </button>
        {!root && (
          <button className="icon-btn" onClick={() => ctx.update(group.id, () => null)} title="Eliminar grupo">
            ✕
          </button>
        )}
      </div>

      {group.children.length === 0 ? (
        <p className="muted small qb-empty">
          {root ? 'Añade condiciones para refinar la búsqueda. Puedes anidar grupos Y / O.' : 'Grupo vacío'}
        </p>
      ) : (
        <ol className="qb-children">
          {group.children.map((child, i) => (
            <li key={child.id}>
              {i > 0 && <span className="qb-connector">{group.op === 'and' ? 'Y' : 'O'}</span>}
              {isGroup(child) ? <GroupEditor group={child} ctx={ctx} /> : <ConditionEditor cond={child} ctx={ctx} />}
            </li>
          ))}
        </ol>
      )}
    </div>
  )
}

function ConditionEditor({ cond, ctx }: { cond: Condition; ctx: Ctx }) {
  const field = ctx.byKey[cond.field]
  const groups = useMemo(() => {
    const out: Record<string, FieldDef[]> = {}
    ctx.fields.forEach((f) => (out[f.group] ??= []).push(f))
    return out
  }, [ctx.fields])
  if (!field) return null

  const set = (patch: Partial<Condition>) => ctx.update(cond.id, (n) => ({ ...(n as Condition), ...patch }))

  return (
    <div className={`qb-cond ${cond.not ? 'negated' : ''}`}>
      <button className={`not-toggle ${cond.not ? 'on' : ''}`} onClick={() => set({ not: !cond.not })} title="Negar">
        NO
      </button>
      <select
        className="input"
        value={cond.field}
        onChange={(e) => {
          const f = ctx.byKey[e.target.value]
          set({ field: f.key, operator: f.operators[0], value: defaultValue(f, f.operators[0]) })
        }}
      >
        {Object.entries(groups).map(([g, fs]) => (
          <optgroup key={g} label={g}>
            {fs.map((f) => (
              <option key={f.key} value={f.key}>
                {f.label}
              </option>
            ))}
          </optgroup>
        ))}
      </select>
      <select
        className="input"
        value={cond.operator}
        onChange={(e) => set({ operator: e.target.value, value: defaultValue(field, e.target.value) })}
      >
        {field.operators.map((op) => (
          <option key={op} value={op}>
            {OPERATOR_LABELS[op] ?? op}
          </option>
        ))}
      </select>
      <ValueEditor field={field} operator={cond.operator} value={cond.value} facet={ctx.facets[field.key]} onChange={(value) => set({ value })} />
      <button className="icon-btn" onClick={() => ctx.update(cond.id, () => null)} title="Eliminar condición">
        ✕
      </button>
    </div>
  )
}

interface ValueProps {
  field: FieldDef
  operator: string
  value: unknown
  facet?: Facet
  onChange: (v: unknown) => void
}

function ValueEditor({ field, operator, value, facet, onChange }: ValueProps) {
  const listId = useId()
  const options = facet?.values ?? []

  if (operator === 'isnull' || operator === 'is_empty' || field.type === 'boolean') {
    return (
      <select className="input" value={String(value)} onChange={(e) => onChange(e.target.value === 'true')}>
        <option value="true">Sí</option>
        <option value="false">No</option>
      </select>
    )
  }

  if (operator === 'between') {
    const [lo, hi] = Array.isArray(value) ? value : ['', '']
    const num = (v: string) => (v === '' ? '' : Number(v))
    return (
      <span className="qb-range">
        <input className="input" type="number" placeholder="mín" value={lo as string} onChange={(e) => onChange([num(e.target.value), hi])} />
        <span>y</span>
        <input className="input" type="number" placeholder="máx" value={hi as string} onChange={(e) => onChange([lo, num(e.target.value)])} />
      </span>
    )
  }

  if (['in', 'has_any', 'has_all'].includes(operator)) {
    return <MultiValue value={Array.isArray(value) ? (value as string[]) : []} options={options.map((o) => String(o.value))} onChange={onChange} />
  }

  if (field.type === 'number') {
    return (
      <input
        className="input"
        type="number"
        value={value as string}
        onChange={(e) => onChange(e.target.value === '' ? '' : Number(e.target.value))}
      />
    )
  }

  return (
    <>
      <input
        className="input grow"
        list={options.length ? listId : undefined}
        value={value as string}
        placeholder={field.type === 'text' ? 'texto…' : 'valor…'}
        onChange={(e) => onChange(e.target.value)}
      />
      {options.length > 0 && (
        <datalist id={listId}>
          {options.map((o) => (
            <option key={String(o.value)} value={String(o.value)}>{`${o.count} cartas`}</option>
          ))}
        </datalist>
      )}
    </>
  )
}

function MultiValue({ value, options, onChange }: { value: string[]; options: string[]; onChange: (v: string[]) => void }) {
  const listId = useId()
  const [draft, setDraft] = useState('')
  const add = (v: string) => {
    const t = v.trim()
    if (t && !value.includes(t)) onChange([...value, t])
    setDraft('')
  }
  return (
    <span className="multi-value grow">
      {value.map((v) => (
        <span key={v} className="tag">
          {v}
          <button onClick={() => onChange(value.filter((x) => x !== v))} aria-label={`Quitar ${v}`}>
            ×
          </button>
        </span>
      ))}
      <input
        className="input"
        list={listId}
        value={draft}
        placeholder="añadir…"
        onChange={(e) => {
          const v = e.target.value
          // Al elegir una opción del datalist se añade directamente
          if (options.includes(v)) add(v)
          else setDraft(v)
        }}
        onKeyDown={(e) => {
          if (e.key === 'Enter') {
            e.preventDefault()
            add(draft)
          }
          if (e.key === 'Backspace' && !draft && value.length) onChange(value.slice(0, -1))
        }}
      />
      <datalist id={listId}>
        {options.filter((o) => !value.includes(o)).map((o) => (
          <option key={o} value={o} />
        ))}
      </datalist>
    </span>
  )
}
