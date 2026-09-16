import { beforeEach, describe, expect, it } from 'vitest'

import { $displaySections, setDisplaySectionsFromConfig } from './display-sections'

describe('setDisplaySectionsFromConfig', () => {
  beforeEach(() => {
    setDisplaySectionsFromConfig(undefined)
  })

  it('hides every section for a profile shaped like cali/link/scout/scribe/switch', () => {
    setDisplaySectionsFromConfig({
      details_mode: 'hidden',
      sections: { thinking: 'hidden', tools: 'hidden', subagents: 'hidden', activity: 'hidden' },
      show_reasoning: false
    })

    expect($displaySections.get()).toEqual({ activity: 'hidden', subagents: 'hidden', thinking: 'hidden', tools: 'hidden' })
  })

  it('defaults thinking/tools open, activity closed, and subagents to the global mode when nothing is configured', () => {
    setDisplaySectionsFromConfig({})

    expect($displaySections.get()).toEqual({
      activity: 'hidden',
      subagents: 'collapsed',
      thinking: 'expanded',
      tools: 'expanded'
    })
  })

  it('hides thinking when only the legacy show_reasoning switch is off, with no sections block at all', () => {
    setDisplaySectionsFromConfig({ show_reasoning: false })

    expect($displaySections.get().thinking).toBe('hidden')
  })

  it('hides thinking when sections.thinking is explicit even though show_reasoning is left on', () => {
    setDisplaySectionsFromConfig({ sections: { thinking: 'hidden' }, show_reasoning: true })

    expect($displaySections.get().thinking).toBe('hidden')
  })

  it('an explicit per-section override wins over the global details_mode for every other section', () => {
    setDisplaySectionsFromConfig({ details_mode: 'hidden', sections: { tools: 'expanded' } })

    const visibility = $displaySections.get()

    expect(visibility.tools).toBe('expanded')
    expect(visibility.subagents).toBe('hidden')
    expect(visibility.activity).toBe('hidden')
  })

  it('ignores an unrelated profile config with no display block (a future profile with nothing set)', () => {
    setDisplaySectionsFromConfig(null)

    expect($displaySections.get()).toEqual({
      activity: 'hidden',
      subagents: 'collapsed',
      thinking: 'expanded',
      tools: 'expanded'
    })
  })
})
