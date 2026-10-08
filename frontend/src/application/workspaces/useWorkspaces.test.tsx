import { describe, expect, it, vi } from 'vitest'
import { renderHook, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import type { ReactNode } from 'react'
import { useCreateWorkspace, useWorkspaces } from './useWorkspaces'
import * as workspacesApi from '../../infrastructure/workspaces/api'

function wrapper({ children }: { children: ReactNode }) {
  const queryClient = new QueryClient()
  return <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
}

describe('useWorkspaces', () => {
  it('fetches the list of workspaces', async () => {
    vi.spyOn(workspacesApi, 'listWorkspaces').mockResolvedValue([
      { id: 'w1', name: 'Acme', slug: 'acme' },
    ])
    const { result } = renderHook(() => useWorkspaces(), { wrapper })

    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(result.current.data).toEqual([{ id: 'w1', name: 'Acme', slug: 'acme' }])
  })

  it('creates a workspace', async () => {
    const createSpy = vi
      .spyOn(workspacesApi, 'createWorkspace')
      .mockResolvedValue({ id: 'w2', name: 'Beta', slug: 'beta' })
    const { result } = renderHook(() => useCreateWorkspace(), { wrapper })

    result.current.mutate('Beta')

    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(createSpy).toHaveBeenCalledWith('Beta')
  })
})
