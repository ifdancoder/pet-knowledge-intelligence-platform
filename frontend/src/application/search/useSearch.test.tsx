import { describe, expect, it, vi } from 'vitest'
import { renderHook, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import type { ReactNode } from 'react'
import { useSearch } from './useSearch'
import * as searchApi from '../../infrastructure/search/api'

function wrapper({ children }: { children: ReactNode }) {
  const queryClient = new QueryClient()
  return <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
}

describe('useSearch', () => {
  it('does not search when the query is empty', () => {
    const searchSpy = vi.spyOn(searchApi, 'search')
    renderHook(() => useSearch('w1', ''), { wrapper })
    expect(searchSpy).not.toHaveBeenCalled()
  })

  it('searches when the query is non-empty', async () => {
    const searchSpy = vi
      .spyOn(searchApi, 'search')
      .mockResolvedValue([{ chunkId: 'c1', sourceId: 's1', text: 'hello', score: 0.9 }])
    const { result } = renderHook(() => useSearch('w1', 'hello'), { wrapper })

    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(searchSpy).toHaveBeenCalledWith('w1', 'hello')
    expect(result.current.data).toEqual([{ chunkId: 'c1', sourceId: 's1', text: 'hello', score: 0.9 }])
  })
})
