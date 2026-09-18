import { AssistantRuntimeProvider, type ThreadMessage, useExternalStoreRuntime } from '@assistant-ui/react'
import { cleanup, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it } from 'vitest'

import { setDisplaySectionsFromConfig } from '@/store/display-sections'

import { stubThreadEnvironment } from '../test-utils'

import { Thread } from '.'

// Live Bot Chat transcripts render two dedicated inter-agent chrome paths
// outside the tool-row pipeline: the incoming "Message from X" card
// (user-message.tsx AgentMessageNote) and the outgoing "Replied to X"
// collapse/disclosure (assistant-message.tsx InterAgentCollapsedNotice).
// Neither was gated by `display.sections.tools` — this pins that both drop
// to no DOM when hidden while the bot's actual answer stays visible through
// the ordinary (uncollapsed) message body.
stubThreadEnvironment()

const createdAt = new Date('2026-05-01T00:00:00.000Z')

afterEach(() => {
  cleanup()
  setDisplaySectionsFromConfig(undefined)
})

function incomingDeliveryMessage(): ThreadMessage {
  return {
    id: 'user-1',
    role: 'user',
    content: [{ type: 'text', text: 'Message from 🤖 cali (@cali): can you check the deploy?' }],
    attachments: [],
    createdAt,
    metadata: { custom: {} }
  } as unknown as ThreadMessage
}

function replyMessage(): ThreadMessage {
  return {
    id: 'assistant-1',
    role: 'assistant',
    content: [{ type: 'text', text: 'Deploy looks healthy.' }],
    status: { type: 'complete', reason: 'stop' },
    createdAt,
    metadata: { unstable_state: null, unstable_annotations: [], unstable_data: [], steps: [], custom: {} }
  } as unknown as ThreadMessage
}

function Harness() {
  const runtime = useExternalStoreRuntime<ThreadMessage>({
    messages: [incomingDeliveryMessage(), replyMessage()],
    isRunning: false,
    onNew: async () => {}
  })

  return (
    <AssistantRuntimeProvider runtime={runtime}>
      <Thread />
    </AssistantRuntimeProvider>
  )
}

describe('inter-agent delivery/readback cards honor display.sections.tools (hidden)', () => {
  it('drops the incoming "Message from" card and the outgoing "Replied to" collapse, keeping the final reply', async () => {
    setDisplaySectionsFromConfig({ sections: { tools: 'hidden' } })

    render(<Harness />)

    expect(await screen.findByText('Deploy looks healthy.')).toBeTruthy()
    expect(screen.queryByText(/Message from cali/)).toBeNull()
    expect(screen.queryByText(/Replied to cali/)).toBeNull()
    expect(screen.queryByText('show message')).toBeNull()
    expect(screen.queryByText('show reply')).toBeNull()
  })
})

describe('inter-agent delivery/readback cards render normally when tools is not hidden (regression)', () => {
  it('still shows the incoming "Message from" card and the outgoing "Replied to" collapse', async () => {
    setDisplaySectionsFromConfig({})

    render(<Harness />)

    expect(await screen.findByText(/Message from cali/)).toBeTruthy()
    expect(screen.getByText(/Replied to cali/)).toBeTruthy()
  })
})
