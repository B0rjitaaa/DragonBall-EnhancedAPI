import { Fragment, useEffect, useRef, useState, type ReactNode } from 'react'
import type { SkillIndex } from '../lib/skills'

// [Habilidades] y los trozos cambiados por una errata (⟦+nuevo⟧ / ⟦-antes⟧, ver errataText).
const TOKEN = /(\[[^\]]+\]|⟦[+-][^⟧]*⟧)/g
const COST = /(\((?:Red|Blue|Green|Yellow|Black|White)\))/g
const IS_COST = /^\((?:Red|Blue|Green|Yellow|Black|White)\)$/

interface Props {
  text: string
  skills: SkillIndex
  onKeyword?: (raw: string) => void
}

/** Color de la etiqueta de una habilidad, como en la carta impresa. */
function kwClass(raw: string): string {
  const k = raw.toLowerCase()
  if (k.startsWith('auto')) return 'auto'
  if (k.startsWith('activate')) return 'activate'
  if (k.startsWith('permanent')) return 'permanent'
  if (k.startsWith('counter')) return 'counter'
  if (k.startsWith('awaken')) return 'awaken'
  return 'skill'
}

/** El coste de color dentro del texto, «(Red)», como un punto de su color. */
function withCostDots(part: string, key: string): ReactNode {
  return part.split(COST).map((p, i) =>
    IS_COST.test(p) ? <i key={`${key}-${i}`} className={`dot sm c-${p.slice(1, -1).toLowerCase()}`} title={p.slice(1, -1)} /> : <Fragment key={`${key}-${i}`}>{p}</Fragment>,
  )
}

/** Texto de Bandai (con <br>) con las habilidades [Entre Corchetes] resaltadas en su color: al pulsarlas se
 *  ve su explicación oficial (con «Filter by» para buscar cartas con esa habilidad). */
export default function CardText({ text, skills, onKeyword }: Props) {
  const [open, setOpen] = useState<{ raw: string; key: string } | null>(null)
  const box = useRef<HTMLDivElement>(null)
  useEffect(() => {
    if (!open) return
    const onDown = (e: PointerEvent) => !box.current?.contains(e.target as Node) && setOpen(null)
    const onKey = (e: KeyboardEvent) => e.key === 'Escape' && (e.stopPropagation(), setOpen(null))
    document.addEventListener('pointerdown', onDown)
    document.addEventListener('keydown', onKey, true)
    return () => {
      document.removeEventListener('pointerdown', onDown)
      document.removeEventListener('keydown', onKey, true)
    }
  }, [open])
  if (!text) return null
  const lines = text.replace(/<br\s*\/?>/gi, '\n').replace(/<[^>]+>/g, '').split('\n')
  return (
    <div className="card-text" ref={box}>
      {lines.map((line, i) => (
        <p key={i}>
          {line.split(TOKEN).map((part, j) => {
            const key = `${i}-${j}`
            if (part.startsWith('⟦+')) return <ins key={key}>{part.slice(2, -1)}</ins>
            if (part.startsWith('⟦-')) return <del key={key}>{part.slice(2, -1)}</del>
            if (!(part.startsWith('[') && part.endsWith(']'))) return <Fragment key={key}>{withCostDots(part, key)}</Fragment>
            const raw = part.slice(1, -1)
            const skill = skills.describe(part)
            const isOpen = open?.key === key
            return (
              <span key={key} className="kw-wrap">
                <button
                  type="button"
                  className={`kw ${kwClass(raw)}`}
                  aria-expanded={isOpen}
                  aria-label={`${raw}: what it means`}
                  onClick={() => setOpen(isOpen ? null : { raw, key })}
                >
                  {raw}
                </button>
                {isOpen && (
                  <span className="kw-pop" role="tooltip">
                    <strong>{skill ? skill.name : raw}</strong>
                    <span>{skill?.description ?? 'Not listed on the official keyword skills page.'}</span>
                    {onKeyword && (
                      <button type="button" className="link small" onClick={() => onKeyword(raw)}>
                        Filter cards with [{raw}] →
                      </button>
                    )}
                  </span>
                )}
              </span>
            )
          })}
        </p>
      ))}
    </div>
  )
}

/** El texto vigente de una carta con errata: la frase antigua cambiada por la nueva y lo que cambió marcado
 *  (⟦+…⟧); con `printed`, el texto impreso con lo que se quitó marcado (⟦-…⟧). */
export function errataText(text: string, before: string, after: string, printed = false): string {
  const clean = (s: string) => s.replace(/[’‘]/g, "'")
  const [t, b, a] = [clean(text), clean(before), clean(after)]
  if (!b || !t.includes(b)) return printed ? text : t.includes(a) ? t : text
  const x = b.split(/(\s+)/)
  const y = a.split(/(\s+)/)
  let i = 0
  while (i < x.length && i < y.length && x[i] === y[i]) i++
  let j = 0
  while (j < x.length - i && j < y.length - i && x[x.length - 1 - j] === y[y.length - 1 - j]) j++
  const pre = y.slice(0, i).join('')
  const post = y.slice(y.length - j).join('')
  const oldMid = x.slice(i, x.length - j).join('')
  const newMid = y.slice(i, y.length - j).join('')
  const marked = printed ? `${pre}${oldMid.trim() ? `⟦-${oldMid}⟧` : ''}${post}` : `${pre}${newMid.trim() ? `⟦+${newMid}⟧` : ''}${post}`
  return t.replace(b, marked)
}
