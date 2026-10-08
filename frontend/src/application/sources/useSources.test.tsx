import { describe, expect, it, vi } from 'vitest'
import { renderHook, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import type { ReactNode } from 'react'
import { useSources, useUploadSource } from './useSources'
import * as sourcesApi from '../../infrastructure/sources/api'

function wrapper({ children }: { children: ReactNode }) {
  const queryClient = new QueryClient()
  return <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
}

describe('useSources', () => {
  it('lists sources for the given workspace', async () => {
    vi.spyOn(sourcesApi, 'listSources').mockResolvedValue([
      { sourceId: 's1', status: 'queued', error: null },
    ])
    const { result } = renderHook(() => useSources('w1'), { wrapper })

    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(result.current.data).toEqual([{ sourceId: 's1', status: 'queued', error: null }])
    expect(sourcesApi.listSources).toHaveBeenCalledWith('w1')
  })

  it('uploads a source', async () => {
    const uploadSpy = vi
      .spyOn(sourcesApi, 'uploadSource')
      .mockResolvedValue({ sourceId: 's2', status: 'queued', error: null })
    const { result } = renderHook(() => useUploadSource('w1'), { wrapper })
    const file = new File(['hello'], 'notes.md', { type: 'text/markdown' })

    result.current.mutate(file)

    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(uploadSpy).toHaveBeenCalledWith('w1', file)
  })
})
