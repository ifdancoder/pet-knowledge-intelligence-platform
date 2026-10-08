import { afterEach, describe, expect, it } from 'vitest'
import {
  clearTokens,
  getAccessToken,
  getRefreshToken,
  setAccessToken,
  setRefreshToken,
} from './tokenStore'

afterEach(() => {
  clearTokens()
})

describe('tokenStore', () => {
  it('keeps the access token only in memory', () => {
    setAccessToken('access-123')
    expect(getAccessToken()).toBe('access-123')
    expect(localStorage.getItem('kip_access_token')).toBeNull()
  })

  it('persists the refresh token in localStorage', () => {
    setRefreshToken('refresh-123')
    expect(getRefreshToken()).toBe('refresh-123')
    expect(localStorage.getItem('kip_refresh_token')).toBe('refresh-123')
  })

  it('clearTokens removes both', () => {
    setAccessToken('a')
    setRefreshToken('r')
    clearTokens()
    expect(getAccessToken()).toBeNull()
    expect(getRefreshToken()).toBeNull()
  })
})
