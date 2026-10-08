import { useMutation } from '@tanstack/react-query'
import * as authApi from '../../infrastructure/auth/api'

export function useRegister() {
  return useMutation({
    mutationFn: ({ email, password }: { email: string; password: string }) =>
      authApi.register(email, password),
  })
}

export function useVerifyEmail() {
  return useMutation({
    mutationFn: (token: string) => authApi.verifyEmail(token),
  })
}

export function useLogin() {
  return useMutation({
    mutationFn: ({ email, password }: { email: string; password: string }) =>
      authApi.login(email, password),
  })
}

export function useLogout() {
  return useMutation({
    mutationFn: () => authApi.logout(),
  })
}
