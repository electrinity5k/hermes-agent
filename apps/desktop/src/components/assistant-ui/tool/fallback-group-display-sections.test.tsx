import { cleanup, render, screen } from '@testing-library/react'
import type { ComponentProps, ReactNode } from 'react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { I18nProvider } from '@/i18n'
import { setDisplaySectionsFromConfig } from '@/store/display-sections'

// `ToolGroupSlot`/`ToolRun` and the row fallback it wraps all read live thread
// state through `useAuiState` — stub it to a plain selector over a
// module-level fixture, same pattern as message-parts-display-sections.test.tsx,
// so this mounts without a full AssistantRuntimeProvider.
let auiState: unknown = { message: { id: 'm1', parts: [], status: { type: 'complete' } }, thread: { isRunning: false, messages: [] } }

vi.mock('@assistant-ui/react', async importOriginal => ({
  ...(await importOriginal<Record<string, unknown>>()),
  useAuiState: (select: (state: unknown) => unknown) => select(auiState)
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
// `el.animate(...)` on mount.
Element.prototype.animate = function animate() {
  return { cancel() {}, finished: Promise.resolve() } as unknown as Animation
}

const { ToolGroupSlot } = await import('./fallback')
const { MESSAGE_PARTS_COMPONENTS } = await import('@/components/assistant-ui/thread/message-parts')

const Fallback = MESSAGE_PARTS_COMPONENTS.tools.Fallback

type FallbackProps = ComponentProps<typeof Fallback>

function withProviders(node: ReactNode) {
  return <I18nProvider configClient={null} initialLocale="en">{node}</I18nProvider>
}

/** Two ordinary `search_files` calls — the "Explored 2 files" summary
 *  category — settled successfully. */
function exploreParts(): FallbackProps[] {
  return [
    {
      args: { pattern: '*.ts' },
      completedAt: 100,
      isError: false,
      result: { matches: ['a.ts'] },
      timestamp: 90,
      toolCallId: 'call-1',
      toolName: 'search_files'
    },
    {
      args: { pattern: '*.tsx' },
      completedAt: 110,
      isError: false,
      result: { matches: ['b.tsx'] },
      timestamp: 105,
      toolCallId: 'call-2',
      toolName: 'search_files'
    }
  ] as unknown as FallbackProps[]
}

function messagePartsFrom(parts: FallbackProps[]) {
  return parts.map(part => ({ ...part, type: 'tool-call' }))
}

function renderGroup(parts: FallbackProps[]) {
  auiState = {
    message: { id: 'm1', parts: messagePartsFrom(parts), status: { type: 'complete' } },
    thread: { isRunning: false, messages: [{ id: 'm1', role: 'assistant' }] }
  }

  return render(
    withProviders(
      <ToolGroupSlot endIndex={parts.length - 1} startIndex={0}>
        {parts.map(part => (
          <Fallback key={part.toolCallId} {...part} />
        ))}
      </ToolGroupSlot>
    )
  )
}

afterEach(() => {
  cleanup()
  setDisplaySectionsFromConfig(undefined)
})

describe('grouped tool-run summaries honor display.sections.tools (hidden)', () => {
  it('renders no DOM for a settled run of ordinary successful calls once tools is hidden', () => {
    setDisplaySectionsFromConfig({ sections: { tools: 'hidden' } })

    const { container } = renderGroup(exploreParts())

    expect(container.innerHTML).toBe('')
  })

  it('drops the summary header but keeps a failed call in the run visible and debuggable', () => {
    setDisplaySectionsFromConfig({ sections: { tools: 'hidden' } })

    const parts = exploreParts()
    parts[1] = { ...parts[1], isError: true, result: { error: 'boom' } }

    const { container } = renderGroup(parts)

    expect(screen.queryByText(/Explored/)).toBeNull()
    expect(container.innerHTML).not.toBe('')
  })

  it('drops the summary header but keeps a dangling (sealed-without-result) call visible', () => {
    setDisplaySectionsFromConfig({ sections: { tools: 'hidden' } })

    const parts = exploreParts()
    parts[1] = { ...parts[1], completedAt: 110, result: undefined }

    const { container } = renderGroup(parts)

    expect(screen.queryByText(/Explored/)).toBeNull()
    expect(container.innerHTML).not.toBe('')
  })
})

describe('grouped tool-run summaries render normally when tools is not hidden (regression)', () => {
  it('still shows the "Explored 2 files" summary line', () => {
    setDisplaySectionsFromConfig({})

    renderGroup(exploreParts())

    expect(screen.getByText(/Explored 2 files/)).toBeTruthy()
  })
})
