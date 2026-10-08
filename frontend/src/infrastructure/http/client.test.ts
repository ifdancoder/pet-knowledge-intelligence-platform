import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { apiRequest, rawRequest, refreshSession } from './client'
import { clearTokens, getAccessToken, setAccessToken, setRefreshToken } from './tokenStore'

function jsonResponse(status: number, body: unknown): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json' },
  })
}

describe('client', () => {
  beforeEach(() => {
    vi.stubGlobal('fetch', vi.fn())
  })

  afterEach(() => {
    clearTokens()
    vi.unstubAllGlobals()
  })

  it('rawRequest sends no Authorization header', async () => {
    const fetchMock = vi.mocked(fetch)
    fetchMock.mockResolvedValueOnce(jsonResponse(200, { ok: true }))

    await rawRequest('/api/v1/auth/login', { method: 'POST', body: '{}' })

    const [, init] = fetchMock.mock.calls[0]
    const headers = init?.headers as Record<string, string>
    expect(headers.Authorization).toBeUndefined()
  })

  it('rawRequest throws ApiError with the backend error code on failure', async () => {
    const fetchMock = vi.mocked(fetch)
    fetchMock.mockResolvedValueOnce(
      jsonResponse(401, { error: { code: 'invalid_credentials', message: 'Bad password' } }),
    )

    await expect(rawRequest('/api/v1/auth/login', { method: 'POST' })).rejects.toMatchObject({
      status: 401,
      code: 'invalid_credentials',
    })
  })

  it('apiRequest attaches the Authorization header when an access token is set', async () => {
    setAccessToken('token-abc')
    const fetchMock = vi.mocked(fetch)
    fetchMock.mockResolvedValueOnce(jsonResponse(200, { ok: true }))

    await apiRequest('/api/v1/workspaces')

    const [, init] = fetchMock.mock.calls[0]
    const headers = init?.headers as Record<string, string>
    expect(headers.Authorization).toBe('Bearer token-abc')
  })

  it('apiRequest refreshes once on 401 and retries the request', async () => {
    setAccessToken('expired')
    setRefreshToken('refresh-xyz')
    const fetchMock = vi.mocked(fetch)
    fetchMock
      .mockResolvedValueOnce(jsonResponse(401, { error: { code: 'access_token_expired', message: 'x' } }))
      .mockResolvedValueOnce(jsonResponse(200, { access_token: 'fresh', refresh_token: 'refresh-new' }))
      .mockResolvedValueOnce(jsonResponse(200, { data: 'result' }))

    const result = await apiRequest<{ data: string }>('/api/v1/workspaces')

    expect(result).toEqual({ data: 'result' })
    expect(getAccessToken()).toBe('fresh')
    expect(fetchMock).toHaveBeenCalledTimes(3)
  })

  it('apiRequest clears tokens and throws when refresh itself fails', async () => {
    setAccessToken('expired')
    setRefreshToken('refresh-xyz')
    const fetchMock = vi.mocked(fetch)
    fetchMock
      .mockResolvedValueOnce(jsonResponse(401, { error: { code: 'access_token_expired', message: 'x' } }))
      .mockResolvedValueOnce(
        jsonResponse(401, { error: { code: 'invalid_or_expired_token', message: 'x' } }),
      )

    await expect(apiRequest('/api/v1/workspaces')).rejects.toMatchObject({ code: 'session_expired' })
    expect(getAccessToken()).toBeNull()
  })

  it('refreshSession returns false when there is no refresh token', async () => {
    expect(await refreshSession()).toBe(false)
  })
})
