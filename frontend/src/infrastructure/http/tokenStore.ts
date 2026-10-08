const REFRESH_TOKEN_KEY = 'kip_refresh_token'

let accessToken: string | null = null

export function getAccessToken(): string | null {
  return accessToken
}

export function setAccessToken(token: string | null): void {
  accessToken = token
}

export function getRefreshToken(): string | null {
  return localStorage.getItem(REFRESH_TOKEN_KEY)
}

export function setRefreshToken(token: string | null): void {
  if (token === null) {
    localStorage.removeItem(REFRESH_TOKEN_KEY)
  } else {
    localStorage.setItem(REFRESH_TOKEN_KEY, token)
  }
}

export function clearTokens(): void {
  setAccessToken(null)
  setRefreshToken(null)
}
