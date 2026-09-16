import { cleanup, render, screen } from '@testing-library/react'
import { atom } from 'nanostores'
import type { ComponentProps, ReactNode } from 'react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { type SessionView, SessionViewProvider } from '@/app/chat/session-view'
import { I18nProvider } from '@/i18n'
import { $displaySections, setDisplaySectionsFromConfig } from '@/store/display-sections'

// `ReasoningAccordionGroup`/`ChainToolFallback`'s nested rows read live thread
// state through `useAuiState`, and the leaf text parts through
// `useMessagePartText`/`useMessagePartReasoning` (assistant-ui's context
// selectors) — stub them to plain selectors over module-level fixtures, same
// pattern as fallback-preview-scope.test.tsx, so these mount without a full
// AssistantRuntimeProvider.
let auiState: unknown = { message: { id: 'm1', parts: [], status: { type: 'complete' } }, thread: { isRunning: false } }
let partText = ''

vi.mock('@assistant-ui/react', async importOriginal => ({
  ...(await importOriginal<Record<string, unknown>>()),
  useAuiState: (select: (state: unknown) => unknown) => select(auiState),
  useMessagePartReasoning: () => ({ status: { type: 'complete' }, text: partText }),
  useMessagePartText: () => ({ status: { type: 'complete' }, text: partText })
}))

vi.stubGlobal(
  'ResizeObserver',
  class {
    disconnect() {}
    observe() {}
    unobserve() {}
  }
)

// jsdom has no Web Animations API; useEnterAnimation's ref callback calls
// `el.animate(...)` on mount (ThinkingDisclosure, ToolFallback).
Element.prototype.animate = function animate() {
  return { cancel() {}, finished: Promise.resolve() } as unknown as Animation
}

const { MESSAGE_PARTS_COMPONENTS } = await import('./message-parts')
const { ToolFallback } = await import('@/components/assistant-ui/tool/fallback')

function sessionView(): SessionView {
  return {
    ...({} as SessionView),
    $messages: atom([]),
    $runtimeId: atom<null | string>('session-1'),
    kind: 'primary'
  } as SessionView
}

function withProviders(node: ReactNode) {
  return (
    <I18nProvider configClient={null} initialLocale="en">
      <SessionViewProvider value={sessionView()}>{node}</SessionViewProvider>
    </I18nProvider>
  )
}

afterEach(() => {
  cleanup()
  setDisplaySectionsFromConfig(undefined)
  partText = ''
})

describe('reasoning disclosure honors display.sections.thinking', () => {
  it('renders no DOM for a live-streaming reasoning block once thinking is hidden', () => {
    setDisplaySectionsFromConfig({ sections: { thinking: 'hidden' } })
    auiState = {
      message: {
        id: 'm1',
        parts: [{ type: 'reasoning', text: 'Planning the search' }],
        status: { type: 'running' }
      },
      thread: { isRunning: true }
    }

    const { ReasoningGroup } = MESSAGE_PARTS_COMPONENTS

    const { container } = render(
      withProviders(
        <ReasoningGroup endIndex={0} startIndex={0}>
          <div>Planning the search</div>
        </ReasoningGroup>
      )
    )

    expect(container.innerHTML).toBe('')
  })

  it('renders no DOM for a settled reasoning block (resumed transcript history) once thinking is hidden', () => {
    setDisplaySectionsFromConfig({ show_reasoning: false })
    auiState = {
      message: { id: 'm1', parts: [{ type: 'reasoning', text: 'Already thought about this' }], status: { type: 'complete' } },
      thread: { isRunning: false }
    }

    const { ReasoningGroup } = MESSAGE_PARTS_COMPONENTS

    const { container } = render(
      withProviders(
        <ReasoningGroup endIndex={0} startIndex={0}>
          <div>Already thought about this</div>
        </ReasoningGroup>
      )
    )

    expect(container.innerHTML).toBe('')
  })

  it('renders the Thinking disclosure when the section is not hidden', () => {
    setDisplaySectionsFromConfig({})
    auiState = {
      message: { id: 'm1', parts: [{ type: 'reasoning', text: 'Planning the search' }], status: { type: 'running' } },
      thread: { isRunning: true }
    }

    const { ReasoningGroup } = MESSAGE_PARTS_COMPONENTS
    render(
      withProviders(
        <ReasoningGroup endIndex={0} startIndex={0}>
          <div>Planning the search</div>
        </ReasoningGroup>
      )
    )

    expect(screen.getByText('Thinking')).toBeTruthy()
  })
})

describe('ordinary tool rows honor display.sections.tools', () => {
  const Fallback = MESSAGE_PARTS_COMPONENTS.tools.Fallback

  const ordinaryToolProps = {
    args: { pattern: '*.ts' },
    completedAt: 100,
    isError: false,
    result: { matches: ['a.ts'] },
    timestamp: 90,
    toolCallId: 'call-1',
    toolName: 'search_files'
  } as unknown as ComponentProps<typeof Fallback>

  it('renders no DOM for an ordinary successful tool call once tools is hidden', () => {
    setDisplaySectionsFromConfig({ sections: { tools: 'hidden' } })

    const { container } = render(withProviders(<Fallback {...ordinaryToolProps} />))

    expect(container.innerHTML).toBe('')
  })

  it('still renders a failed tool call so it stays debuggable, even with tools hidden', () => {
    setDisplaySectionsFromConfig({ sections: { tools: 'hidden' } })

    const { container } = render(withProviders(<Fallback {...ordinaryToolProps} isError result={{ error: 'boom' }} />))

    expect(container.innerHTML).not.toBe('')
  })

  it('still renders a live, unanswered clarify question with tools hidden', () => {
    setDisplaySectionsFromConfig({ sections: { tools: 'hidden' } })

    const { container } = render(
      withProviders(
        <Fallback
          {...ordinaryToolProps}
          args={{ question: 'Which environment?' }}
          completedAt={undefined}
          result={undefined}
          toolName="clarify"
        />
      )
    )

    expect(container.innerHTML).not.toBe('')
  })

  it('renders the ordinary tool row when tools is not hidden', () => {
    setDisplaySectionsFromConfig({})

    const { container } = render(withProviders(<ToolFallback {...ordinaryToolProps} />))

    expect(container.innerHTML).not.toBe('')
  })
})

describe('final assistant text stays visible regardless of hidden sections', () => {
  it('the Text part still renders the final reply when every detail section is hidden', () => {
    setDisplaySectionsFromConfig({
      sections: { activity: 'hidden', subagents: 'hidden', thinking: 'hidden', tools: 'hidden' },
      show_reasoning: false
    })
    expect($displaySections.get()).toEqual({ activity: 'hidden', subagents: 'hidden', thinking: 'hidden', tools: 'hidden' })

    partText = 'Here is the final answer.'

    const { Text } = MESSAGE_PARTS_COMPONENTS

    render(withProviders(<Text completedAt={100} status={{ type: 'complete' }} text={partText} timestamp={90} type="text" />))

    expect(screen.getByText('Here is the final answer.')).toBeTruthy()
  })
})
