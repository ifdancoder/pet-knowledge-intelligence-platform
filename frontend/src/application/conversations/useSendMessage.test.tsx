import { describe, expect, it, vi } from 'vitest'
import { act, renderHook, waitFor } from '@testing-library/react'
import { useSendMessage } from './useSendMessage'
import * as sseClient from '../../infrastructure/conversations/sseClient'

describe('useSendMessage', () => {
  it('accumulates deltas into pendingContent then finalizes on done', async () => {
    vi.spyOn(sseClient, 'streamAssistantReply').mockImplementation(
      async (_workspaceId, _conversationId, _content, onEvent) => {
        onEvent({ type: 'delta', delta: 'Hel' })
        onEvent({ type: 'delta', delta: 'lo' })
        onEvent({ type: 'done', messageId: 'm1' })
      },
    )
    const onMessageFinalized = vi.fn()
    const { result } = renderHook(() => useSendMessage('w1', 'c1', onMessageFinalized))

    await act(async () => {
      await result.current.send('hi')
    })

    await waitFor(() => expect(result.current.isStreaming).toBe(false))
    expect(onMessageFinalized).toHaveBeenCalledWith({
      id: 'm1',
      role: 'assistant',
      content: 'Hello',
      sourceChunkIds: [],
    })
    expect(result.current.pendingContent).toBe('')
  })

  it('surfaces a stream error without finalizing a message', async () => {
    vi.spyOn(sseClient, 'streamAssistantReply').mockImplementation(
      async (_workspaceId, _conversationId, _content, onEvent) => {
        onEvent({ type: 'error', message: 'LLM unavailable' })
      },
    )
    const onMessageFinalized = vi.fn()
    const { result } = renderHook(() => useSendMessage('w1', 'c1', onMessageFinalized))

    await act(async () => {
      await result.current.send('hi')
    })

    expect(result.current.streamError).toBe('LLM unavailable')
    expect(onMessageFinalized).not.toHaveBeenCalled()
  })
})
