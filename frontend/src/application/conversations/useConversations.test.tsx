import { describe, expect, it, vi } from 'vitest'
import { renderHook, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import type { ReactNode } from 'react'
import { useConversations, useCreateConversation, useMessages } from './useConversations'
import * as conversationsApi from '../../infrastructure/conversations/api'

function wrapper({ children }: { children: ReactNode }) {
  const queryClient = new QueryClient()
  return <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
}

describe('useConversations', () => {
  it('lists conversations for the workspace', async () => {
    vi.spyOn(conversationsApi, 'listConversations').mockResolvedValue([{ id: 'c1' }])
    const { result } = renderHook(() => useConversations('w1'), { wrapper })

    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(result.current.data).toEqual([{ id: 'c1' }])
  })

  it('creates a conversation', async () => {
    const createSpy = vi.spyOn(conversationsApi, 'createConversation').mockResolvedValue({ id: 'c2' })
    const { result } = renderHook(() => useCreateConversation('w1'), { wrapper })

    result.current.mutate()

    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(createSpy).toHaveBeenCalledWith('w1')
  })

  it('fetches messages for a conversation', async () => {
    vi.spyOn(conversationsApi, 'getMessages').mockResolvedValue([
      { id: 'm1', role: 'user', content: 'hi', sourceChunkIds: [] },
    ])
    const { result } = renderHook(() => useMessages('w1', 'c1'), { wrapper })

    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(result.current.data).toEqual([{ id: 'm1', role: 'user', content: 'hi', sourceChunkIds: [] }])
  })

  it('does not fetch messages when there is no conversation yet', () => {
    const getMessagesSpy = vi.spyOn(conversationsApi, 'getMessages')
    renderHook(() => useMessages('w1', ''), { wrapper })
    expect(getMessagesSpy).not.toHaveBeenCalled()
  })
})
