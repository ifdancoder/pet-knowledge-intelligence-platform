import { clearTokens, getAccessToken, getRefreshToken, setAccessToken, setRefreshToken } from './tokenStore'

const BASE_URL = import.meta.env.VITE_API_URL

interface TokenPairDto {
  access_token: string
  refresh_token: string
}

export class ApiError extends Error {
  status: number
  code: string

  constructor(status: number, code: string, message: string) {
    super(message)
    this.status = status
    this.code = code
  }
}

async function parseError(response: Response): Promise<ApiError> {
  let body: unknown = null
  try {
    body = await response.json()
  } catch {
    body = null
  }
  if (body !== null && typeof body === 'object' && 'error' in body) {
    const err = (body as { error: { code: string; message: string } }).error
    return new ApiError(response.status, err.code, err.message)
  }
  return new ApiError(response.status, 'unknown_error', response.statusText)
}

export async function rawRequest<T>(path: string, init: RequestInit = {}): Promise<T> {
  const response = await fetch(`${BASE_URL}${path}`, {
    ...init,
    headers: { 'Content-Type': 'application/json', ...init.headers },
  })
  if (!response.ok) {
    throw await parseError(response)
  }
  if (response.status === 204) {
    return undefined as T
  }
  return (await response.json()) as T
}

export async function refreshSession(): Promise<boolean> {
  const refreshToken = getRefreshToken()
  if (!refreshToken) {
    return false
  }
  try {
    const tokens = await rawRequest<TokenPairDto>('/api/v1/auth/refresh', {
      method: 'POST',
      body: JSON.stringify({ refresh_token: refreshToken }),
    })
    setAccessToken(tokens.access_token)
    setRefreshToken(tokens.refresh_token)
    return true
  } catch {
    clearTokens()
    return false
  }
}

export async function apiRequest<T>(path: string, init: RequestInit = {}, isRetry = false): Promise<T> {
  const accessToken = getAccessToken()
  const headers: Record<string, string> = {
    ...(init.body instanceof FormData ? {} : { 'Content-Type': 'application/json' }),
    ...(init.headers as Record<string, string> | undefined),
  }
  if (accessToken) {
    headers.Authorization = `Bearer ${accessToken}`
  }

  const response = await fetch(`${BASE_URL}${path}`, { ...init, headers })

  if (response.status === 401 && !isRetry) {
    const refreshed = await refreshSession()
    if (!refreshed) {
      window.dispatchEvent(new Event('kip:session-expired'))
      throw new ApiError(401, 'session_expired', 'Session expired, please log in again')
    }
    return apiRequest<T>(path, init, true)
  }

  if (!response.ok) {
    throw await parseError(response)
  }
  if (response.status === 204) {
    return undefined as T
  }
  return (await response.json()) as T
}
