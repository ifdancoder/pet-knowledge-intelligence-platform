import { rawRequest } from '../http/client'
import { setAccessToken, setRefreshToken, clearTokens, getRefreshToken } from '../http/tokenStore'

interface TokenPairDto {
  access_token: string
  refresh_token: string
}

export async function register(email: string, password: string): Promise<string> {
  const response = await rawRequest<{ user_id: string }>('/api/v1/auth/register', {
    method: 'POST',
    body: JSON.stringify({ email, password }),
  })
  return response.user_id
}

export async function verifyEmail(token: string): Promise<void> {
  await rawRequest<void>('/api/v1/auth/verify-email', {
    method: 'POST',
    body: JSON.stringify({ token }),
  })
}

export async function login(email: string, password: string): Promise<void> {
  const tokens = await rawRequest<TokenPairDto>('/api/v1/auth/login', {
    method: 'POST',
    body: JSON.stringify({ email, password }),
  })
  setAccessToken(tokens.access_token)
  setRefreshToken(tokens.refresh_token)
}

export async function logout(): Promise<void> {
  const refreshToken = getRefreshToken()
  clearTokens()
  if (refreshToken) {
    await rawRequest<void>('/api/v1/auth/logout', {
      method: 'POST',
      body: JSON.stringify({ refresh_token: refreshToken }),
    }).catch(() => undefined)
  }
}
