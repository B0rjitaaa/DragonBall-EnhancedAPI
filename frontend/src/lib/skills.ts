import { normalizeKeyword } from './query'
import type { FacetValue, KeywordSkill, KeywordSkillsResponse, SkillCategory } from './types'

/** Campo de filtro de cada categoría oficial. */
export const CATEGORY_FIELD: Record<SkillCategory, string> = {
  timing: 'timing',
  skill: 'keyword_skill',
  keyword: 'keyword_rule',
}

export const CATEGORY_LABEL: Record<SkillCategory, string> = {
  timing: 'Activate Timing',
  skill: 'Keyword Skills',
  keyword: 'Keywords',
}

export class SkillIndex {
  readonly byName: Map<string, KeywordSkill>
  readonly data: KeywordSkillsResponse
  constructor(data: KeywordSkillsResponse) {
    this.data = data
    this.byName = new Map(data.skills.map((s) => [s.name, s]))
  }

  static empty(): SkillIndex {
    return new SkillIndex({ updated: '', source: '', skills: [], variants: {}, aliases: {}, deck_rules: {} })
  }

  /** '[Activate : Main]', 'Over Realm 3', 'Once per turn' -> nombre oficial ('Activate : Main', 'Over Realm X'…) */
  officialName(raw: string): string {
    const norm = normalizeKeyword(raw.replace(/^\[|\]$/g, ''))
    return this.data.aliases[norm] ?? norm
  }

  /** Skill oficial con su texto, o null si no está en la web oficial (p. ej. Z-Stack). */
  describe(raw: string): KeywordSkill | null {
    return this.byName.get(raw) ?? this.byName.get(this.officialName(raw)) ?? null
  }

  /** Campo de filtro para una habilidad; las no oficiales van a Keyword Skills. */
  fieldFor(name: string): string {
    const skill = this.byName.get(name)
    return skill ? CATEGORY_FIELD[skill.category] : 'keyword_skill'
  }

  variants(name: string): FacetValue[] {
    return this.data.variants[name] ?? []
  }

  deckRule(name: string): string | undefined {
    return this.data.deck_rules[name]
  }
}
