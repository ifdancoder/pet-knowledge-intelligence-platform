import { describe, expect, it, vi } from 'vitest'
import { renderHook, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import type { ReactNode } from 'react'
import { useLogin, useRegister } from './useAuth'
import * as authApi from '../../infrastructure/auth/api'

function wrapper({ children }: { children: ReactNode }) {
  const queryClient = new QueryClient()
  return <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
}

describe('useAuth', () => {
  it('useRegister calls the register API with email and password', async () => {
    const registerSpy = vi.spyOn(authApi, 'register').mockResolvedValue('user-1')
    const { result } = renderHook(() => useRegister(), { wrapper })

    result.current.mutate({ email: 'a@example.com', password: 'longenoughpassword' })

    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(registerSpy).toHaveBeenCalledWith('a@example.com', 'longenoughpassword')
  })

  it('useLogin calls the login API with email and password', async () => {
    const loginSpy = vi.spyOn(authApi, 'login').mockResolvedValue(undefined)
    const { result } = renderHook(() => useLogin(), { wrapper })

    result.current.mutate({ email: 'a@example.com', password: 'longenoughpassword' })

    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(loginSpy).toHaveBeenCalledWith('a@example.com', 'longenoughpassword')
  })
})
