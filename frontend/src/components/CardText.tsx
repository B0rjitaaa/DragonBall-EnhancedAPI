import { Fragment, useEffect, useRef, useState, type ReactNode } from 'react'
import { decodeEntities, plainCardText } from '../lib/cardText'
import type { SkillIndex } from '../lib/skills'

// [Habilidades] y los trozos cambiados por una errata (⟦+nuevo⟧ / ⟦-antes⟧, ver errataText).
const TOKEN = /(\[[^\]]+\]|⟦[+-][^⟧]*⟧)/g

// Costes dentro del texto. Bandai los escribe de muchas formas: «(Green)», «((Green))», «(G)», «(緑)» o «(黒)»
// para uno de color, y «①», «(1)», «(１)» o «(X)» para uno de cualquier color.
const COLOR_WORDS = 'Red|Blue|Green|Yellow|Black|White'
const COLOR_CODE: Record<string, string> = {
  G: 'green', Y: 'yellow', R: 'red', 赤: 'red', 青: 'blue', 緑: 'green', 黄: 'yellow', 黒: 'black', 白: 'white',
}
const COLOR_COST = `\\(\\((?:${COLOR_WORDS})\\)\\)|\\((?:${COLOR_WORDS}|[GYR赤青緑黄黒白])\\)`
const ANY_COST = '[①-⑳]|\\((?:[0-9０-９]{1,2}|X)\\)'
const COST = new RegExp(`(${COLOR_COST}|${ANY_COST})`, 'g')
const IS_COLOR_COST = new RegExp(`^(?:${COLOR_COST})$`)
const IS_ANY_COST = new RegExp(`^(?:${ANY_COST})$`)

function colorOf(token: string): string {
  const inner = token.replace(/[()]/g, '')
  return COLOR_CODE[inner] ?? inner.toLowerCase()
}

/** Coste genérico (de cualquier color): «①», «(1)», «(１)» o «(X)» → su número. */
function amountOf(token: string): string {
  const c = token.codePointAt(0) ?? 0
  if (c >= 0x2460 && c <= 0x2473) return String(c - 0x2460 + 1)
  return token.slice(1, -1).replace(/[０-９]/g, (d) => String.fromCharCode(d.charCodeAt(0) - 0xfee0))
}

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

/** Los costes dentro del texto: los de color como un punto de su color y los genéricos como un círculo con su número. */
function withCostDots(part: string, key: string): ReactNode {
  return part.split(COST).map((p, i) => {
    const k = `${key}-${i}`
    if (IS_COLOR_COST.test(p)) {
      const color = colorOf(p)
      return <i key={k} className={`dot sm c-${color}`} title={`${color[0].toUpperCase()}${color.slice(1)} energy`} />
    }
    if (IS_ANY_COST.test(p)) {
      const n = amountOf(p)
      return (
        <i key={k} className="cost-any" title={`${n} energy of any color`}>
          {n}
        </i>
      )
    }
    return <Fragment key={k}>{p}</Fragment>
  })
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
  const lines = plainCardText(text).split('\n')
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
  // Con «<» y «>» de verdad en los tres, así la frase de la errata se encuentra aunque uno venga con «&lt;».
  const clean = (s: string) => decodeEntities(s).replace(/[’‘]/g, "'")
  const [t, b, a] = [clean(text), clean(before), clean(after)]
  if (!b || !t.includes(b)) return t
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
