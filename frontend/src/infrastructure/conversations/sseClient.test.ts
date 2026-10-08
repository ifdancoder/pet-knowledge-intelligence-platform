import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { streamAssistantReply, type StreamEvent } from './sseClient'
import { setAccessToken, clearTokens } from '../http/tokenStore'

function sseResponse(chunks: string[]): Response {
  const encoder = new TextEncoder()
  let index = 0
  const stream = new ReadableStream<Uint8Array>({
    pull(controller) {
      if (index < chunks.length) {
        controller.enqueue(encoder.encode(chunks[index]))
        index += 1
      } else {
        controller.close()
      }
    },
  })
  return new Response(stream, { status: 200 })
}

describe('streamAssistantReply', () => {
  beforeEach(() => {
    setAccessToken('token-abc')
    vi.stubGlobal('fetch', vi.fn())
  })

  afterEach(() => {
    clearTokens()
    vi.unstubAllGlobals()
  })

  it('emits delta then done events parsed from the SSE stream', async () => {
    vi.mocked(fetch).mockResolvedValueOnce(
      sseResponse([
        'data: {"delta": "Hel"}\n\n',
        'data: {"delta": "lo"}\n\n',
        'data: {"done": true, "message_id": "m1"}\n\n',
      ]),
    )
    const events: StreamEvent[] = []

    await streamAssistantReply('w1', 'c1', 'hi', (event) => events.push(event))

    expect(events).toEqual([
      { type: 'delta', delta: 'Hel' },
      { type: 'delta', delta: 'lo' },
      { type: 'done', messageId: 'm1' },
    ])
  })

  it('emits an error event on a mid-stream error payload', async () => {
    vi.mocked(fetch).mockResolvedValueOnce(sseResponse(['data: {"error": "LLM unavailable"}\n\n']))
    const events: StreamEvent[] = []

    await streamAssistantReply('w1', 'c1', 'hi', (event) => events.push(event))

    expect(events).toEqual([{ type: 'error', message: 'LLM unavailable' }])
  })

  it('emits an error event when the request itself fails', async () => {
    vi.mocked(fetch).mockResolvedValueOnce(new Response(null, { status: 500 }))
    const events: StreamEvent[] = []

    await streamAssistantReply('w1', 'c1', 'hi', (event) => events.push(event))

    expect(events).toEqual([{ type: 'error', message: 'Request failed with status 500' }])
  })
})
