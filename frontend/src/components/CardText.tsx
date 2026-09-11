import { Fragment } from 'react'
import type { SkillIndex } from '../lib/skills'
import Tooltip from './Tooltip'

const TOKEN = /(\[[^\]]+\])/g

interface Props {
  text: string
  skills: SkillIndex
  onKeyword?: (raw: string) => void
}

/** Texto de Bandai (con <br>) con las habilidades [Entre Corchetes] resaltadas, con su
 *  explicación oficial al pasar el ratón y clicables para filtrar. */
export default function CardText({ text, skills, onKeyword }: Props) {
  if (!text) return null
  const lines = text.replace(/<br\s*\/?>/gi, '\n').replace(/<[^>]+>/g, '').split('\n')
  return (
    <div className="card-text">
      {lines.map((line, i) => (
        <p key={i}>
          {line.split(TOKEN).map((part, j) => {
            if (!(part.startsWith('[') && part.endsWith(']'))) return <Fragment key={j}>{part}</Fragment>
            const skill = skills.describe(part)
            return (
              <Tooltip key={j} title={skill ? `[${skill.name}]` : undefined} text={skill?.description} footer="Clic para filtrar">
                <button className="kw" onClick={() => onKeyword?.(part.slice(1, -1))}>
                  {part}
                </button>
              </Tooltip>
            )
          })}
        </p>
      ))}
    </div>
  )
}
