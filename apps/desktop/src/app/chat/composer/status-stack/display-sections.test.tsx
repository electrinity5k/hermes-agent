import { cleanup, render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router'
import { afterEach, expect, it, vi } from 'vitest'

import { $backgroundStatusBySession } from '@/store/composer-status'
import { setDisplaySectionsFromConfig } from '@/store/display-sections'
import { $goalsBySession } from '@/store/goals'
import { $subagentsBySession, upsertSubagent } from '@/store/subagents'

import { ComposerStatusStack } from './index'

vi.mock('@/lib/use-enter-animation', () => ({ useEnterAnimation: () => undefined }))

vi.stubGlobal(
  'ResizeObserver',
  class {
    disconnect() {}
    observe() {}
    unobserve() {}
  }
)

const stack = () => (
  <MemoryRouter>
    <ComposerStatusStack queue={null} sessionId="owner" />
  </MemoryRouter>
)

afterEach(() => {
  cleanup()
  $backgroundStatusBySession.set({})
  $goalsBySession.set({})
  $subagentsBySession.set({})
  setDisplaySectionsFromConfig(undefined)
})

it('renders no background row — no DOM at all, not just collapsed — once activity is hidden, live or historical', () => {
  setDisplaySectionsFromConfig({ sections: { activity: 'hidden' } })
  $backgroundStatusBySession.set({
    owner: [{ id: 'process', type: 'background', state: 'running', title: 'Background process' }]
  })

  render(stack())

  expect(screen.queryByRole('button', { name: /Background/ })).toBeNull()
})

it('leaves the Goal Mode indicator alone — it is primary status, not ambient activity meta', () => {
  setDisplaySectionsFromConfig({ sections: { activity: 'hidden' } })
  $goalsBySession.set({ owner: { status: 'active', title: 'A goal', updatedAt: 1 } })

  render(stack())

  expect(screen.getByRole('button', { name: /Goal active/ })).toBeTruthy()
})

it('renders the background row when activity is not hidden (regression guard)', () => {
  // `activity` defaults to hidden even with an empty config (ambient meta is
  // noise by default, matching the TUI's own SECTION_DEFAULTS) — so proving
  // this row can render at all requires an explicit non-hidden override.
  setDisplaySectionsFromConfig({ sections: { activity: 'expanded' } })
  $backgroundStatusBySession.set({
    owner: [{ id: 'process', type: 'background', state: 'running', title: 'Background process' }]
  })

  render(stack())

  expect(screen.getByRole('button', { name: /Background/ })).toBeTruthy()
})

it('renders no subagent roster — no DOM at all — once subagents is hidden, even while one is actively running', () => {
  setDisplaySectionsFromConfig({ sections: { subagents: 'hidden' } })
  upsertSubagent('owner', { subagent_id: 'worker', goal: 'Worker task' })

  render(stack())

  expect(screen.queryByRole('button', { name: /Subagent/ })).toBeNull()
  expect(screen.queryByText('Worker task')).toBeNull()
})

it('renders the subagent roster when subagents is not hidden (regression guard)', () => {
  setDisplaySectionsFromConfig({})
  upsertSubagent('owner', { subagent_id: 'worker', goal: 'Worker task' })

  render(stack())

  expect(screen.getByRole('button', { name: /1 Subagent/ })).toBeTruthy()
})
